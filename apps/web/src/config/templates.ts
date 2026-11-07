import type { CitationStyle, ProjectTemplate, ResearchLevel } from "@/lib/api";

export const TEMPLATES: {
  id: ProjectTemplate;
  name: string;
  description: string;
  sections: string[];
}[] = [
  {
    id: "thesis",
    name: "Thesis (5-Chapter)",
    description: "Standard dissertation structure from Introduction to Recommendations.",
    sections: [
      "Abstract",
      "Chapter One: Introduction",
      "Chapter Two: Literature Review",
      "Chapter Three: Methodology",
      "Chapter Four: Results and Discussion",
      "Chapter Five: Summary, Conclusion and Recommendations",
      "References",
      "Appendices",
    ],
  },
  {
    id: "journal_article",
    name: "Journal Article",
    description: "IMRaD structure for peer-reviewed papers and seminar submissions.",
    sections: [
      "Abstract",
      "1. Introduction",
      "2. Related Work",
      "3. Methodology",
      "4. Results",
      "5. Discussion",
      "6. Conclusion",
      "References",
    ],
  },
  {
    id: "report",
    name: "Research Report",
    description: "Structured investigation report for professional and policy research.",
    sections: [
      "Executive Summary",
      "Background & Objectives",
      "Methodology & Sources",
      "Key Findings",
      "Recommendations",
      "References",
    ],
  },
  {
    id: "blank",
    name: "Blank Workspace",
    description: "Start with a clean slate and define your own sections.",
    sections: ["Untitled Section", "References"],
  },
];

export const RESEARCH_LEVELS: { id: ResearchLevel; label: string }[] = [
  { id: "undergraduate", label: "Undergraduate" },
  { id: "postgraduate", label: "Postgraduate (Master’s / PhD)" },
  { id: "professional", label: "Professional / Analyst" },
];

export const CITATION_STYLES: { id: CitationStyle; label: string }[] = [
  { id: "apa7", label: "APA 7th edition" },
  { id: "harvard", label: "Harvard" },
  { id: "ieee", label: "IEEE" },
];
