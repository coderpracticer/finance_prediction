export interface FactorScore {
  name: string;
  group: string;
  score: number;
  confidence: number;
  raw_value?: number | string | null;
  evidence: string;
}

export interface Candidate {
  symbol: string;
  name: string;
  market: string;
  rank: number;
  opportunity_score: number;
  confidence: number;
  data_quality: string;
  factors: FactorScore[];
  thesis: string;
  risks: string[];
}

export interface ScreeningResponse {
  run_id: string;
  status: string;
  candidates: Candidate[];
  warnings: string[];
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function runScreening(limit = 10): Promise<ScreeningResponse> {
  const response = await fetch(`${API_BASE_URL}/api/screening-runs?limit=${limit}`, {
    method: "POST"
  });
  if (!response.ok) {
    throw new Error(`Screening failed: ${response.status}`);
  }
  return response.json();
}

export async function fetchLatestScreening(): Promise<ScreeningResponse> {
  const response = await fetch(`${API_BASE_URL}/api/screening-runs/latest`);
  if (!response.ok) {
    throw new Error(`Failed to load latest screening: ${response.status}`);
  }
  return response.json();
}

export interface ChatResponse {
  session_id: string;
  symbol?: string;
  answer: string;
  used_candidate_context: boolean;
}

export async function askCandidateQuestion(
  symbol: string,
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      symbol,
      message,
      session_id: sessionId
    })
  });
  if (!response.ok) {
    throw new Error(`Chat failed: ${response.status}`);
  }
  return response.json();
}
