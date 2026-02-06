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
  detailed_explanation?: string;
}

export interface Contact {
  name: string;
  email: string;
  location: string;
  phone: string;
  linkedin: string;
  github: string;
}

export interface JobExperience {
  job_title: string;
  company_name: string;
  location: string;
  from_date: string;
  to_date: string;
  experience: string[];
}

export interface Skill {
  title: string;
  skills: string;
}

export interface Education {
  degree: string;
  major: string;
  college: string;
  from_date: string;
  to_date: string;
}

export interface Certification {
  title: string;
  obtained_date: string;
  expiry_date: string;
}

export interface ApplicationAnswer {
  questions: string;
  answer: string;
}

export interface ApplicationAnswers {
  all_answers: ApplicationAnswer[];
}

export interface ProfileData {
  contact: Contact;
  job_exp: JobExperience[];
  skills: Skill[];
  education: Education[];
  certification: Certification[];
}
