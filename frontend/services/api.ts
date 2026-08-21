import axios from "axios";
import {
  ResultsData,
  SDGClassificationRequest,
  SDGClassificationResponse,
} from "@/types/main";

// Keep in sync with the port the Flask backend binds in backend/app.py.
const API_BASE_URL = "http://127.0.0.1:8010/";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const sdgApi = {
  classifyAurora: async (
    data: SDGClassificationRequest,
  ): Promise<SDGClassificationResponse> => {
    const response = await apiClient.post<SDGClassificationResponse>(
      "api/classify_aurora",
      data,
    );
    return response.data;
  },

  classifySTUrl: async (
    data: SDGClassificationRequest,
  ): Promise<SDGClassificationResponse> => {
    const response = await apiClient.post<SDGClassificationResponse>(
      "api/classify_st_url",
      data,
    );
    return response.data;
  },
};

// Helper to get classification by model

export const classifyByModel = async (
  modelType: "aurora" | "st-url",
  data: SDGClassificationRequest,
): Promise<SDGClassificationResponse> => {
  switch (modelType) {
    case "aurora":
      return sdgApi.classifyAurora(data);
    case "st-url":
      return sdgApi.classifySTUrl(data);
    default:
      console.warn(`Unknown model type: ${modelType}, defaulting to Aurora`);
      return sdgApi.classifyAurora(data);
  }
};
