export type SourceType = 'website' | 'social' | 'company' | 'product' | 'service';

export interface ResearchRun {
  id: string;
  source_type: SourceType;
  source_input: string;
  status: 'queued' | 'validating' | 'crawling' | 'extracting' | 'analyzing' | 'discovering_competitors' | 'verifying_competitors' | 'generating_reports' | 'completed' | 'failed';
  current_step: string;
  progress_percentage: number;
  error_message?: string;
  google_doc_url?: string;
  pdf_url?: string;
  created_at: string;
  updated_at: string;
}

export interface CompetitorItem {
  competitor_name: string;
  website: string;
  domain: string;
  competitor_type: string;
  confidence_level: string;
  reason: string;
  description?: string;
  products?: string[];
  pricing_model?: string;
  key_features?: string[];
  top_keywords?: string[];
  competitive_overlap?: string;
  google_rank?: number;
  evidence_urls: string[];
  deep_extracted?: boolean;
}

export interface ResearchSummary {
  run: ResearchRun;
  company?: {
    company_name: string;
    domain: string;
    website: string;
    industry: string;
    description: string;
  };
  competitors: CompetitorItem[];
  pages_count: number;
  products_count: number;
  services_count: number;
  keywords_count: number;
}
