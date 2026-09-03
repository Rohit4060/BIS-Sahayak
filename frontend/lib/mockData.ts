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
    description: "Identify the exact Indian Standard that applies to your product category.",
    prompt: "Which Indian Standard applies to my product?",
  },
  {
    id: "certification-guidance",
    title: "Certification Guidance",
    description: "Walk through the ISI Mark or CRS certification process step by step.",
    prompt: "Guide me through the certification process for my product.",
  },
  {
    id: "testing-requirements",
    title: "Testing Requirements",
    description: "See mandatory test parameters, sample sizes and lab prerequisites.",
    prompt: "What tests are required before I can get certified?",
  },
  {
    id: "laboratory-finder",
    title: "Laboratory Finder",
    description: "Locate BIS-recognised testing laboratories near your facility.",
    prompt: "Find a BIS-recognised laboratory near me.",
  },
];

export const stats: Stat[] = [
  { label: "BIS documents indexed", value: "6" },
  { label: "Grounded knowledge chunks", value: "176" },
  { label: "Citation source", value: "Database" },
];

export const sampleQueries: string[] = [
  "IS code for LED bulbs?",
  "CRS registration steps for chargers",
  "Hallmarking requirement for jewellery",
  "Is BIS certification mandatory for toys?",
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
