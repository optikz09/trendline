//+------------------------------------------------------------------+
//|                                    TrendLineTradingBridge.mq4      |
//|   File-based bridge between the Python TrendLine bot and MT4/PRO4  |
//|   (HugosWay). Exports rates for the bot to read, and executes the  |
//|   OPEN commands the bot queues. Attach to ONE chart of the symbol  |
//|   you trade, on the H1+ timeframe you configured in the bot.       |
//|                                                                    |
//|   Files live in the terminal's MQL4\Files sandbox. Point the bot's |
//|   --bridge at that folder (or sync it there).                      |
//+------------------------------------------------------------------+
#property strict

extern string BridgeSubfolder = "trendline_bridge"; // under MQL4\Files
extern int    ExportBars      = 600;                 // history bars to export each new bar
extern int    PollSeconds     = 5;                   // how often to check for commands
extern int    Slippage        = 30;                  // points
extern int    MagicNumber     = 770412;              // tags this EA's orders
extern double MaxSpreadPoints  = 0;                  // 0 = ignore; else skip if spread wider

int      lastProcessed = 0;      // highest command line index already executed
datetime lastBarTime   = 0;

string RatesFile()    { return BridgeSubfolder + "\\" + Symbol() + "_" + IntegerToString(PeriodMinutes()) + "_rates.csv"; }
string CommandsFile() { return BridgeSubfolder + "\\commands.jsonl"; }
string AcksFile()     { return BridgeSubfolder + "\\acks.jsonl"; }
int    PeriodMinutes(){ return Period(); }           // MT4 Period() already returns minutes

//+------------------------------------------------------------------+
int OnInit()
  {
   if(Period() < 60)
      Print("WARNING: TrendLine bot targets H1 and above; current TF is ", Period(), "m.");
   EventSetTimer(PollSeconds);
   ExportRates();
   lastProcessed = CountAcks();
   Print("TrendLineTradingBridge ready. Rates -> ", RatesFile(), "  Commands <- ", CommandsFile());
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason) { EventKillTimer(); }

//+------------------------------------------------------------------+
//| Export on each new bar; poll commands on the timer.              |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(Time[0] != lastBarTime)
     {
      lastBarTime = Time[0];
      ExportRates();
     }
  }

void OnTimer() { ProcessCommands(); }

//+------------------------------------------------------------------+
//| Write the latest OHLC history the Python bot reads.             |
//+------------------------------------------------------------------+
void ExportRates()
  {
   int fh = FileOpen(RatesFile(), FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) { Print("Cannot write rates: ", GetLastError()); return; }
   FileWrite(fh, "time,open,high,low,close,volume");
   int bars = MathMin(ExportBars, Bars);
   // oldest -> newest so the bot sees ascending time
   for(int i = bars - 1; i >= 0; i--)
     {
      string line = TimeToString(Time[i], TIME_DATE | TIME_MINUTES) + "," +
                    DoubleToString(Open[i], Digits) + "," +
                    DoubleToString(High[i], Digits) + "," +
                    DoubleToString(Low[i], Digits) + "," +
                    DoubleToString(Close[i], Digits) + "," +
                    DoubleToString((double)Volume[i], 0);
      FileWrite(fh, line);
     }
   FileClose(fh);
  }

//+------------------------------------------------------------------+
//| Count how many commands we have already acked.                  |
//+------------------------------------------------------------------+
int CountAcks()
  {
   int fh = FileOpen(AcksFile(), FILE_READ | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) return 0;
   int n = 0;
   while(!FileIsEnding(fh)) { FileReadString(fh); n++; }
   FileClose(fh);
   return n;
  }

//+------------------------------------------------------------------+
//| Read commands.jsonl; execute any line beyond lastProcessed.     |
//| One JSON object per line (see FileBridgeBroker protocol).       |
//+------------------------------------------------------------------+
void ProcessCommands()
  {
   int fh = FileOpen(CommandsFile(), FILE_READ | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) return;   // nothing queued yet
   int idx = 0;
   while(!FileIsEnding(fh))
     {
      string line = FileReadString(fh);
      if(StringLen(line) < 2) continue;
      if(idx >= lastProcessed)
        {
         ExecuteCommand(line);
         lastProcessed = idx + 1;
        }
      idx++;
     }
   FileClose(fh);
  }

//+------------------------------------------------------------------+
//| Minimal JSON field extractor (values are flat, no nesting).     |
//+------------------------------------------------------------------+
string JsonStr(string src, string key)
  {
   string pat = "\"" + key + "\"";
   int k = StringFind(src, pat);
   if(k < 0) return "";
   int colon = StringFind(src, ":", k);
   if(colon < 0) return "";
   int i = colon + 1;
   while(i < StringLen(src) && (StringGetChar(src, i) == ' ' || StringGetChar(src, i) == '\"')) i++;
   int start = i;
   while(i < StringLen(src))
     {
      int ch = StringGetChar(src, i);
      if(ch == ',' || ch == '}' || ch == '\"') break;
      i++;
     }
   return StringSubstr(src, start, i - start);
  }

double JsonNum(string src, string key) { return StrToDouble(JsonStr(src, key)); }

//+------------------------------------------------------------------+
void ExecuteCommand(string line)
  {
   string action = JsonStr(line, "action");
   if(action != "OPEN") return;

   string id     = JsonStr(line, "id");
   string sym    = JsonStr(line, "symbol");
   string side   = JsonStr(line, "side");
   double lots   = JsonNum(line, "lots");
   double sl     = JsonNum(line, "sl");
   double tp     = JsonNum(line, "tp");

   if(sym != Symbol())
     { Ack(id, "skipped-symbol"); return; }

   if(MaxSpreadPoints > 0 && (Ask - Bid) / Point > MaxSpreadPoints)
     { Ack(id, "skipped-spread"); return; }

   int    type  = (side == "long") ? OP_BUY : OP_SELL;
   double price = (side == "long") ? Ask : Bid;
   lots = NormalizeLots(lots);

   int ticket = OrderSend(Symbol(), type, lots, price, Slippage, sl, tp,
                          "TL-" + id, MagicNumber, 0, (side == "long") ? clrBlue : clrRed);
   if(ticket < 0)
      Ack(id, "error-" + IntegerToString(GetLastError()));
   else
      Ack(id, "filled-" + IntegerToString(ticket));
  }

//+------------------------------------------------------------------+
double NormalizeLots(double lots)
  {
   double step = MarketInfo(Symbol(), MODE_LOTSTEP);
   double mn   = MarketInfo(Symbol(), MODE_MINLOT);
   double mx   = MarketInfo(Symbol(), MODE_MAXLOT);
   if(step > 0) lots = MathFloor(lots / step) * step;
   if(lots < mn) lots = mn;
   if(lots > mx) lots = mx;
   return NormalizeDouble(lots, 2);
  }

void Ack(string id, string status)
  {
   int fh = FileOpen(AcksFile(), FILE_READ | FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(fh == INVALID_HANDLE) { Print("Cannot ack ", id); return; }
   FileSeek(fh, 0, SEEK_END);
   FileWrite(fh, "{\"id\":\"" + id + "\",\"status\":\"" + status + "\"}");
   FileClose(fh);
   Print("ACK ", id, " -> ", status);
  }
//+------------------------------------------------------------------+
