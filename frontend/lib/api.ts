export type LanguageCode = "en" | "hi" | "bn" | "mr" | "ta" | "te" | "kn" | "ml" | "gu" | "pa";

export const languageOptions: { code: LanguageCode; label: string }[] = [
  { code: "en", label: "English" }, { code: "hi", label: "Hindi" }, { code: "bn", label: "Bengali" },
  { code: "mr", label: "Marathi" }, { code: "ta", label: "Tamil" }, { code: "te", label: "Telugu" },
  { code: "kn", label: "Kannada" }, { code: "ml", label: "Malayalam" }, { code: "gu", label: "Gujarati" }, { code: "pa", label: "Punjabi" },
];

export type Citation = { standard_number?: string | null; clause?: string | null; page?: number | null; source_url?: string | null; source_reference?: string | null };
export type Evidence = { section?: string | null; page?: number | null; excerpt: string };
export type ChatResponse = { reply: string; citations: Citation[] };
export type Recommendation = { standard_number?: string | null; title: string; relevance: string; reason: string; requirement_status: string; evidence: Evidence[]; citations: Citation[] };
export type RecommendResponse = { product_description: string; recommendations: Recommendation[]; message?: string | null };
export type ComplianceRequirement = { requirement: string; status: string; reason: string; testing_requirement?: string | null; next_step?: string | null };
export type ComplianceStandard = { standard_number?: string | null; title: string; requirements: ComplianceRequirement[]; evidence: Evidence[]; citations: Citation[] };
export type ComplianceResponse = { product_description: string; standards: ComplianceStandard[]; limitations: string; message?: string | null };
export type HelpResponse = { question: string; answer: string; key_points: string[]; next_steps: string[]; status: string; citations: Citation[]; limitations: string[] };
export type Lab = { name: string; location?: string | null; testing_capabilities: string[]; standard_numbers: string[]; recognition_or_accreditation?: string | null; reason: string; citations: Citation[] };
export type LabsResponse = { product_description: string; laboratories: Lab[]; message?: string | null; limitations: string[] };

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, body: Record<string, string | undefined>): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!response.ok) {
    let message = "The BIS Sahayak service could not complete this request.";
    try { message = (await response.json() as { detail?: string }).detail ?? message; } catch { /* Use the safe fallback. */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  chat: (message: string, language: LanguageCode) => request<ChatResponse>("/api/chat", { message, language }),
  recommend: (product_description: string) => request<RecommendResponse>("/api/standards/recommend", { product_description }),
  compliance: (product_description: string) => request<ComplianceResponse>("/api/compliance/check", { product_description }),
  hallmarking: (question: string) => request<HelpResponse>("/api/hallmarking/help", { question }),
  consumer: (question: string) => request<HelpResponse>("/api/consumer/help", { question }),
  labs: (product_description: string, standard_number?: string) => request<LabsResponse>("/api/labs/find", { product_description, standard_number }),
};
