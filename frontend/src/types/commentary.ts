export interface CommentaryEntry {
  timestamp: number;          // seconds from session start
  text: string;               // raw commentary text from Gemini
  energyLevel: number;        // 0.0–1.0 heuristic score
  isHighlight: boolean;       // flagged as highlight-worthy
}
