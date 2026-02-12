export interface Job {
  url: string;
  role: string;
  company_name: string;
  date_posted: string;
  date_applied: string;
  jd_path: string;
  resume_id: number;
  resume_score: number;
  job_match_summary: string;
  application_qnas?: Record<string, any>;
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
  certifications: Certification[];
}

// Enums matching backend (using const objects for TypeScript compatibility)
export const EmploymentType = {
  FULL_TIME: "Full-time",
  PART_TIME: "Part-time",
  EITHER: "Either"
} as const;

export type EmploymentType = typeof EmploymentType[keyof typeof EmploymentType];

export const Gender = {
  MALE: "Male",
  FEMALE: "Female",
  NON_BINARY: "Non-binary",
  PREFER_NOT_TO_ANSWER: "Prefer not to answer"
} as const;

export type Gender = typeof Gender[keyof typeof Gender];

export const RaceEthnicity = {
  HISPANIC_LATINO: "Hispanic or Latino",
  WHITE: "White",
  BLACK_AFRICAN_AMERICAN: "Black or African American",
  ASIAN: "Asian",
  AMERICAN_INDIAN_ALASKA_NATIVE: "American Indian or Alaska Native",
  NATIVE_HAWAIIAN_PACIFIC_ISLANDER: "Native Hawaiian or Other Pacific Islander",
  TWO_OR_MORE_RACES: "Two or More Races",
  PREFER_NOT_TO_ANSWER: "Prefer not to answer"
} as const;

export type RaceEthnicity = typeof RaceEthnicity[keyof typeof RaceEthnicity];

export const VeteranStatus = {
  DISABLED_VETERAN: "Disabled veteran",
  RECENTLY_SEPARATED_VETERAN: "Recently separated veteran",
  ACTIVE_WARTIME_VETERAN: "Active wartime veteran",
  ARMED_FORCES_SERVICE_MEDAL_VETERAN: "Armed Forces service medal veteran",
  OTHER_PROTECTED_VETERAN: "Other protected veteran",
  NOT_A_VETERAN: "Not a veteran",
  PREFER_NOT_TO_ANSWER: "Prefer not to answer"
} as const;

export type VeteranStatus = typeof VeteranStatus[keyof typeof VeteranStatus];

export const DisabilityStatus = {
  YES: "Yes, I have a disability",
  NO: "No, I do not have a disability",
  PREFER_NOT_TO_ANSWER: "Prefer not to answer"
} as const;

export type DisabilityStatus = typeof DisabilityStatus[keyof typeof DisabilityStatus];

export const YesNoNA = {
  YES: "Yes",
  NO: "No",
  NA: "N/A"
} as const;

export type YesNoNA = typeof YesNoNA[keyof typeof YesNoNA];

// UserOnboarding interface (35+ fields matching backend)
export interface UserOnboarding {
  // Personal Information
  full_name: string;
  street_address: string;
  city: string;
  state: string;
  zip_code: string;
  phone_number: string;
  email_address: string;
  date_of_birth?: string;
  age_18_or_older: boolean;

  // Work Authorization
  work_eligible_us: boolean;
  visa_sponsorship: boolean;

  // Position Details
  available_start_date: string;
  employment_type: EmploymentType;
  willing_relocate: boolean;
  willing_travel: boolean;
  travel_percentage?: string;

  // Compensation
  desired_salary: string;

  // EEO Information (Voluntary)
  gender?: Gender;
  race_ethnicity?: RaceEthnicity;
  veteran_status?: VeteranStatus;
  disability_status?: DisabilityStatus;

  // Employment History
  current_employee: boolean;
  ever_terminated: boolean;
  termination_explanation?: string;

  // Job-Specific Requirements
  security_clearance: YesNoNA;

  // Certifications and Declarations
  cert_accuracy: boolean;
  cert_dismissal: boolean;
  cert_background_check: boolean;
  cert_drug_testing: boolean;
  cert_at_will: boolean;
  cert_job_description: boolean;
  cert_privacy_notice: boolean;
  cert_data_processing: boolean;

  // Signature
  electronic_signature: string;
  signature_date: string;
}
