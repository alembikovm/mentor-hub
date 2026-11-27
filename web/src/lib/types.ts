export type Role = "mentor" | "mentee";

export interface User {
  id: string;
  email: string | null;
  name: string | null;
  role: Role | null;
  invite_code: string | null;
}

export interface Me extends User {
  mentors: User[];
}

export interface Progress {
  done: number;
  total: number;
  percent: number;
  completed_at: string | null;
}

/** A course. The API calls it a roadmap: the course content is a roadmap tree. */
export interface Roadmap {
  id: string;
  title: string;
  description: string;
  created_at: string;
  topic_count: number;
  mentor: User | null; // mentee view
  progress: Progress | null; // mentee view, or mentor viewing a mentee
  access_count: number | null; // mentor view
}

export interface TopicNode {
  id: string;
  title: string;
  description: string;
  position: number;
  child_count: number;
  done: boolean | null;
  leaves_done: number | null;
  leaves_total: number | null;
  // Sequential unlocking (present when a mentee's progress is shown).
  locked: boolean | null;
  current: boolean | null;
}

export interface NodeDetail {
  roadmap: Roadmap;
  node: TopicNode | null;
  ancestors: TopicNode[];
  children: TopicNode[];
  subject: User | null; // whose progress is shown
}

export interface MenteeCourse {
  roadmap: Roadmap;
  has_access: boolean;
  progress: Progress | null;
}

export interface Mentee extends User {
  joined_at: string;
  courses: MenteeCourse[];
}

export interface CourseMember {
  mentee: User;
  has_access: boolean;
  progress: Progress | null;
}

export interface PreviewNode {
  title: string;
  description: string;
  children: PreviewNode[];
}

export interface RoadmapPreview {
  title: string;
  description: string;
  topic_count: number;
  children: PreviewNode[];
}

export type SubmissionStatus = "pending" | "analyzing" | "done" | "failed";

export interface ReviewIssue {
  severity: "critical" | "major" | "minor";
  title: string;
  detail: string;
  location: string;
}

export interface AiReview {
  verdict: "correct" | "partially_correct" | "incorrect" | "off_topic" | "unreadable";
  score: number;
  summary: string;
  strengths: string[];
  issues: ReviewIssue[];
  suggestions: string[];
  questions_for_mentor: string[];
  perception?: {
    content_type: string;
    transcription: string;
    ui_description: string;
    visible_errors: string[];
  };
}

export interface Submission {
  id: string;
  node_id: string;
  note: string;
  status: SubmissionStatus;
  ai_review: AiReview | null;
  error: string | null;
  mentor_comment: string | null;
  created_at: string;
  images: { id: string; media_type: string }[];
  mentee: User | null;
  topic_title: string | null;
  roadmap_id: string | null;
  topic_path: string[];
}
