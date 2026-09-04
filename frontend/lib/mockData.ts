export type NavItem = { id: string; label: string };
export type QuickAction = { id: string; title: string; description: string; prompt: string };
export type Stat = { label: string; value: string };

export const navItems: NavItem[] = [
  { id: "ask-bis", label: "Ask BIS" },
  { id: "standards", label: "Standards" },
  { id: "compliance", label: "Compliance" },
  { id: "hallmarking", label: "Hallmarking" },
  { id: "consumer", label: "Consumer Help" },
  { id: "laboratories", label: "Laboratories" },
];

export const quickActions: QuickAction[] = [
  {
    id: "find-standard",
    title: "Find Applicable Standard",
    description: "Review standards that are relevant to your product in the retrieved BIS evidence.",
    prompt: "What does IS 302 Part 1 cover?",
  },
  {
    id: "certification-guidance",
    title: "Compliance Evidence",
    description: "Review requirements only when they are supported by the available BIS sources.",
    prompt: "What does IS 302 Part 1 cover?",
  },
  {
    id: "testing-requirements",
    title: "Evidence and Citations",
    description: "See retrieved excerpts and source citations behind each supported result.",
    prompt: "What is IS 17423:2021?",
  },
  {
    id: "laboratory-finder",
    title: "Laboratory Finder",
    description: "Search only the authoritative laboratory records currently available in the database.",
    prompt: "household electrical appliance",
  },
];

export const stats: Stat[] = [
  { label: "BIS documents indexed", value: "6" },
  { label: "Grounded knowledge chunks", value: "176" },
  { label: "Citation source", value: "Database" },
];

export const sampleQueries: string[] = [
  "What does IS 302 Part 1 cover?",
  "What is IS 17423:2021?",
  "What should I know about hallmarking gold jewellery?",
  "What BIS standard applies to a rocket engine?",
];

export const standardCodes: string[] = [
  "IS 302-1",
  "IS 1554-1",
  "IS 15885",
  "IS 16046",
  "IS 4250",
  "IS 13252",
  "IS 10500",
  "IS 733",
];
