export interface Job {
  url: string;
  role: string;
  company_name: string;
  date_posted: string;
  date_applied: string;
  jd_filepath: string;
  cloud: string;
  resume_filepath: string;
  resume_score: number;
  detailed_explaination?: string;
}