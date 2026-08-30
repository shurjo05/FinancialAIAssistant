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
