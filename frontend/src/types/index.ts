// TypeScript mirrors of the backend Pydantic schemas. Keep in sync with
// backend/app/schemas/schemas.py.

export interface Transaction {
  id: number;
  upload_id: number;
  date: string;
  description: string;
  merchant_normalized: string;
  amount: number;
  transaction_type: string;
  category: string;
  category_confidence: number;
  is_recurring: boolean;
  is_anomaly: boolean;
}

export interface Correction {
  id: number;
  transaction_id: number;
  original_category: string;
  corrected_category: string;
  original_confidence: number;
  model_version: string | null;
  created_at: string;
}

export interface TransactionList {
  items: Transaction[];
  total: number;
  page: number;
  page_size: number;
}

export interface ParseError {
  row: number;
  issue: string;
  raw: string;
}

export interface UploadResult {
  upload_id: number;
  filename: string;
  row_count: number;
  error_count: number;
  date_range_start: string | null;
  date_range_end: string | null;
  status: string;
  errors: ParseError[];
}

export interface Subscription {
  id: number;
  upload_id: number;
  merchant_normalized: string;
  amount: number;
  frequency: string;
  last_charged: string;
  occurrence_count: number;
  total_spent: number;
  category: string;
  kind: string;
}

export interface Anomaly {
  id: number;
  upload_id: number;
  transaction_id: number;
  anomaly_type: string;
  z_score: number | null;
  category: string;
  description: string;
}

export interface QueryResponse {
  answer: string;
  provider: string;
  tools_used: string[];
}

export type ChatStyle = "friendly" | "numbers" | "coach";

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  tools_used?: string[] | null;
  provider?: string | null;
  created_at?: string;
}

export interface ConversationSummary {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: ChatMessage[];
}

export interface SendResult {
  conversation_id: number;
  title: string;
  message: ChatMessage;
}

export interface PlaidStatus {
  configured: boolean;
}

export interface LinkTokenResponse {
  link_token: string;
}

export interface PlaidItemResult {
  item_id: string;
  institution_name: string | null;
}

export interface PlaidSyncResult {
  added: number;
  institution_name: string | null;
}

export interface BankAccount {
  id: number;
  name: string;
  institution: string | null;
  mask: string | null;
  type: string;
  subtype: string | null;
  /** Credit/loan: the balance is money owed, not money held. */
  is_liability: boolean;
  current_balance: number | null;
  available_balance: number | null;
  currency: string;
}

export interface AccountBalances {
  count: number;
  assets: number;
  liabilities: number;
  net_worth: number;
  as_of: string | null;
  /** True when these are the demo's synthetic accounts. */
  sample: boolean;
  /** Has a Plaid connection, even if balances haven't loaded yet. */
  bank_connected: boolean;
  accounts: BankAccount[];
}

export interface MerchantTotal {
  merchant: string;
  total: number;
}

export interface Summary {
  total_spending: number;
  total_income: number;
  net: number;
  savings_rate: number;
  transaction_count: number;
  subscription_count: number;
  bill_count: number;
  anomaly_count: number;
  top_merchant: MerchantTotal | null;
  largest_transaction: {
    merchant: string; amount: number; category: string; date: string;
  } | null;
  date_range: { start: string | null; end: string | null };
}

export interface MonthlyPoint {
  month: string;
  spending: number;
  income: number;
}
