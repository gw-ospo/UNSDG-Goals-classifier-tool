export type SDGValue = {
  prediction: number;
  sdg?:
    | string
    | {
        "@type"?: string;
        code?: string;
        icon?: string;
        id?: string;
        label?: string;
        name?: string;
        type?: string;
      };
};

export type Recommendation = {
  reason: string;
  suggestions: string[];
  text_quality: number;
};

export type ResultsData = {
  projectUrl?: string;
  projectName?: string;
  projectDescription?: string;
  recommendation?: Recommendation;
  predictions?:
    | Record<string, SDGValue>
    | Record<string, number>
    | SDGPrediction[]
    | { sdg: string; prediction: number }[];
  [key: string]: unknown;
};

export type ErrorProps = {
  error: string | null;
  setError: (error: string | null) => void;
  setResults: (
    results: {
      sdg_predictions?: Record<string, number>;
      [key: string]: unknown;
    } | null,
  ) => void;
};

export type RawResultsProps = {
  results: unknown;
};

export interface SDGClassificationRequest {
  projectName: string;
  projectUrl: string;
  projectDescription: string;
}

export type SDGPrediction = {
  sdg: string;
  prediction: number;
};

export interface SDGClassificationResponse {
  predictions: (SDGPrediction | { sdg: string; prediction: number })[];
  projectName?: string;
  projectUrl?: string;
  repo_url?: string;
  [key: string]: any;
}

export type SDGCardProps = {
  sdgKey: string;
  confidence: number;
};

export type CardGridProps = {
  sdgPredictions?:
    | SDGValue[]
    | Record<string, SDGValue>
    | Record<string, number>;
};

export type EditModalProps = {
  editableResults: Record<string, SDGValue>;
  setEditableResults: React.Dispatch<
    React.SetStateAction<Record<string, SDGValue>>
  >;
  setIsModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
  saveEditedResults: () => void;
};
