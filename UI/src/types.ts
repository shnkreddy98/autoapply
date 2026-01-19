export interface Job {
  id: string;
  companyName: string;
  jobRole: string;
  resumeMatch: number;
  resumeName: string;
  additionalQuestions?: string[];
}
