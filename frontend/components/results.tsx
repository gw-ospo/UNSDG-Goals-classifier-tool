import { useEffect, useState } from "react";
import JSZip from "jszip";
import { MdDone } from "react-icons/md";
import CardGrid from "./cardGrid";
import RawResults from "./rawResults";
import EditModal from "./editModal";
import { SDGValue, ResultsData } from "@/types/main";
import { IoIosInformationCircleOutline } from "react-icons/io";
import { classifyByModel } from "@/services/api";

/*
Results Component
- Displays the results of the SDG analysis
- Shows SDG cards, allows editing via modal, and downloading results
*/

type ResultsProps = {
  results: ResultsData | null;
  setResults: (value: ResultsData | null) => void;
  setError: (value: string | null) => void;
};

const loadingPhrases = [
  "Scanning repository signals...",
  "Mapping SDG relevance...",
  "Cross-checking project intent...",
  "Preparing your results...",
  "Aligning insights with the SDGs...",
];

const sdgSpinnerColors = [
  "#e5243b",
  "#d81b60",
  "#f4a261",
  "#e9c46a",
  "#4caf50",
  "#2e8b57",
  "#26a69a",
  "#29b6f6",
  "#1976d2",
  "#7b1fa2",
  "#ff6f61",
  "#ff9800",
  "#c0ca33",
  "#8bc34a",
  "#009688",
  "#03a9f4",
  "#3f51b5",
];

const isNoSdgs = (predictions: ResultsData["predictions"]): boolean => {
  if (predictions == null) return true;

  if (Array.isArray(predictions)) {
    return predictions.length === 0;
  }

  if (typeof predictions !== "object") return true;

  const keys = Object.keys(predictions);
  if (keys.length === 0) return true;

  const values = Object.values(predictions as Record<string, unknown>);
  return values.every((v) => {
    if (v == null) return true;
    if (typeof v === "number") return v <= 0;
    if (typeof v === "object" && v !== null && "prediction" in v) {
      const sdgValue = v as SDGValue;
      const num = Number(sdgValue.prediction);
      return !Number.isFinite(num) || num <= 0;
    }
    return true;
  });
};

const Results = ({ results, setResults, setError }: ResultsProps) => {
  const [editableResults, setEditableResults] = useState<
    Record<string, SDGValue>
  >({});

  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<string>("aurora");
  const [isLoadingTab, setIsLoadingTab] = useState(false);
  const [loadingPhraseIndex, setLoadingPhraseIndex] = useState(0);

  const handleTabChange = async (newTab: string) => {
    if (newTab === activeTab || !results) return;

    setIsLoadingTab(true);
    setActiveTab(newTab);

    const requestData = {
      projectName:
        localStorage.getItem("projectName") || results.projectName || "",
      projectUrl:
        localStorage.getItem("projectUrl") || results.projectUrl || "",
      projectDescription:
        localStorage.getItem("projectDescription") ||
        results.projectDescription ||
        "",
    };

    try {
      const response = await classifyByModel(
        newTab as "aurora" | "st-url",
        requestData,
      );

      if (response) {
        setResults(response as ResultsData);
      }
    } catch (error) {
      console.error("Error fetching data for tab:", error);
      setError("Failed to load data for selected model. Please try again.");
    } finally {
      setIsLoadingTab(false);
    }
  };

  useEffect(() => {
    if (!isLoadingTab) {
      return;
    }

    const interval = window.setInterval(() => {
      setLoadingPhraseIndex((prev) => (prev + 1) % loadingPhrases.length);
    }, 1200);

    return () => window.clearInterval(interval);
  }, [isLoadingTab]);

  const getScore = (v: number | SDGValue | null | undefined) =>
    typeof v === "number"
      ? Number(v)
      : Number((v as SDGValue)?.prediction ?? 0);

  const saveEditedResults = () => {
    if (results) {
      setResults({
        ...results,
        predictions: { ...(editableResults ?? {}) },
      });
    }
    setIsModalOpen(false);
    setSaveMessage("SDG predictions updated successfully!");

    setTimeout(() => {
      setSaveMessage(null);
    }, 3000);
  };

  const handleChanges = () => {
    if (results?.predictions) {
      const normalized: Record<string, SDGValue> = {};
      Object.entries(
        results.predictions as Record<string, number | SDGValue>,
      ).forEach(([k, v]) => {
        if (typeof v === "number") {
          normalized[k] = { prediction: v };
        } else {
          normalized[k] = v as SDGValue;
        }
      });
      setEditableResults(normalized);
      setIsModalOpen(true);
    }
  };

  const buildDownloadContent = (
    predictions: Record<string, number | SDGValue>,
    format: "json" | "yaml" | "txt",
  ) => {
    const unsdgData = {
      sdg_analysis: {
        analyzed_at: new Date().toISOString(),
        repositoryName: results?.projectName,
        repositoryUrl: results?.projectUrl,
        predictions,
        summary: {
          total_sdgs: Object.keys(predictions).length,
          high_confidence: Object.values(predictions).filter(
            (score) => getScore(score) >= 0.7,
          ).length,
          medium_confidence: Object.values(predictions).filter(
            (score) => getScore(score) >= 0.4 && getScore(score) < 0.7,
          ).length,
          low_confidence: Object.values(predictions).filter(
            (score) => getScore(score) < 0.4,
          ).length,
        },
      },
    };

    if (format === "json") {
      return {
        content: JSON.stringify(unsdgData, null, 2),
        fileName: "unsdg.json",
        mimeType: "application/json",
      };
    }

    if (format === "yaml") {
      const lines = [
        "sdg_analysis:",
        `  analyzed_at: "${new Date().toISOString()}"`,
        `  repositoryName: "${String(results?.projectName ?? "").replace(/"/g, '\\"')}"`,
        `  repositoryUrl: "${String(results?.projectUrl ?? "").replace(/"/g, '\\"')}"`,
        "  predictions:",
      ];

      Object.entries(predictions).forEach(([key, value]) => {
        if (typeof value === "number") {
          lines.push(`    ${key}: ${value}`);
        } else {
          lines.push(`    ${key}: ${JSON.stringify(value)}`);
        }
      });

      lines.push("  summary:");
      lines.push(`    total_sdgs: ${Object.keys(predictions).length}`);
      lines.push(
        `    high_confidence: ${Object.values(predictions).filter((score) => getScore(score) >= 0.7).length}`,
      );
      lines.push(
        `    medium_confidence: ${Object.values(predictions).filter((score) => getScore(score) >= 0.4 && getScore(score) < 0.7).length}`,
      );
      lines.push(
        `    low_confidence: ${Object.values(predictions).filter((score) => getScore(score) < 0.4).length}`,
      );

      return {
        content: lines.join("\n"),
        fileName: "unsdg.yaml",
        mimeType: "text/yaml",
      };
    }

    const textLines = [
      `Repository: ${results?.projectName ?? "N/A"}`,
      `URL: ${results?.projectUrl ?? "N/A"}`,
      `Analysis generated: ${new Date().toISOString()}`,
      "",
      "SDG Predictions:",
    ];

    Object.entries(predictions).forEach(([key, value]) => {
      textLines.push(`${key}: ${getScore(value).toFixed(4)}`);
    });

    return {
      content: textLines.join("\n"),
      fileName: "unsdg.txt",
      mimeType: "text/plain",
    };
  };

  const handleDownload = async () => {
    if (!results?.predictions || isNoSdgs(results.predictions)) {
      setError("No SDG predictions available.");
      return;
    }

    try {
      const predictions = results.predictions as Record<string, number | SDGValue>;
      const zip = new JSZip();

      const files = [
        buildDownloadContent(predictions, "json"),
        buildDownloadContent(predictions, "yaml"),
        buildDownloadContent(predictions, "txt"),
      ];

      files.forEach((file) => {
        zip.file(file.fileName, file.content);
      });

      const archiveBlob = await zip.generateAsync({ type: "blob" });
      const url = URL.createObjectURL(archiveBlob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "unsdg-analysis.zip";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setSaveMessage("SDG analysis folder downloaded successfully!");

      setTimeout(() => {
        setSaveMessage(null);
      }, 3000);
    } catch {
      setError("Failed to create the download archive.");
    }
  };

  const noSdgs = isNoSdgs(results?.predictions);
  const spinnerGradient = `conic-gradient(from 180deg, ${sdgSpinnerColors
    .map((color, index) => {
      const step = 360 / sdgSpinnerColors.length;
      return `${color} ${index * step}deg ${(index + 1) * step}deg`;
    })
    .join(", ")})`;

  return (
    <div className="min-h-screen bg-gradient-to-br">
      <main className="container mx-auto px-8 py-12">
        <div className="space-y-8">
          {/* Header with back button */}
          <div className="flex items-center justify-between">
            <h1 className="text-4xl font-bold text-black">UN SDG Analysis Results</h1>
            <button
              onClick={() => {
                setResults(null);
                setError(null);
                setSaveMessage(null);
              }}
              className="px-6 py-3 bg-purple-700 hover:bg-purple-800 text-white font-semibold rounded-xl transition-colors duration-200"
            >
              Analyze Another Repository
            </button>
          </div>

          {/* Success Message */}
          {saveMessage && (
            <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg flex items-center">
              <MdDone className="mr-2" />
              {saveMessage}
            </div>
          )}

          {/* Repository URL */}
          <div className="bg-white rounded-xl p-6 shadow-lg">
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Analyzed Repository:</h3>
            <p className="text-purple-700 font-medium break-all">{results?.projectUrl ?? "—"}</p>
          </div>

          {/* Results Display */}
          <div className="space-y-6">
            <h3 className="text-2xl font-semibold text-gray-800">UN SDG Goals Analysis</h3>

            {/* Vertical Tabs Layout */}
            <div className="flex gap-6">
              {/* Sidebar Navigation */}
              <div className="w-64 flex-shrink-0">
                <div className="bg-white rounded-xl shadow-lg p-2 space-y-1">
                  <h4 className="text-sm font-semibold text-gray-600 px-4 py-2">
                    Available Models
                  </h4>

                  <button
                    onClick={() => handleTabChange("aurora")}
                    disabled={isLoadingTab}
                    className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 relative ${
                      activeTab === "aurora"
                        ? "bg-purple-50 text-purple-700 font-semibold"
                        : "text-gray-700 hover:bg-gray-50"
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {activeTab === "aurora" && (
                      <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-8 bg-purple-600 rounded-r-full"></div>
                    )}
                    <span className="ml-2 flex items-center">
                      Aurora Model
                      <span className="relative group inline-block">
                        <IoIosInformationCircleOutline className="ml-2 text-purple-600 cursor-help" />
                        <span className="invisible group-hover:visible absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 px-3 py-2 text-xs text-white bg-gray-800 rounded-lg shadow-lg z-10 whitespace-normal">
                          This is a third party API from EU Alliance Research
                          <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-800"></span>
                        </span>
                      </span>
                    </span>
                  </button>


                  <button
                    onClick={() => handleTabChange("st-url")}
                    disabled={isLoadingTab}
                    className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 relative ${
                      activeTab === "st-url"
                        ? "bg-purple-50 text-purple-700 font-semibold"
                        : "text-gray-700 hover:bg-gray-50"
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {activeTab === "st-url" && (
                      <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-1 h-8 bg-purple-600 rounded-r-full"></div>
                    )}
                    <span className="ml-2">
                      Readme Analyser
                      <span className="relative group inline-block">
                        <IoIosInformationCircleOutline className="ml-2 text-purple-600 cursor-help" />
                        <span className="invisible group-hover:visible absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 px-3 py-2 text-xs text-white bg-gray-800 rounded-lg shadow-lg z-10 whitespace-normal">
                          This is a sentence transformer modal from Huggingface
                          that analyzes the github repository URL and all its metadata.
                          <span className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-gray-800"></span>
                        </span>
                      </span>
                    </span>
                  </button>
                </div>
              </div>

              {/* Main Content Area */}
              <div className="flex-1">
                {isLoadingTab ? (
                  <div className="rounded-3xl border border-purple-100 bg-white/95 p-10 shadow-2xl shadow-purple-900/10 backdrop-blur-sm">
                    <div className="flex flex-col items-center justify-center gap-5 text-center">
                      <div className="relative flex h-24 w-24 items-center justify-center">
                        <div
                          className="absolute inset-0 rounded-full animate-spin"
                          style={{ background: spinnerGradient }}
                        />
                        <div className="absolute inset-2 rounded-full bg-white" />
                        <div className="absolute h-6 w-6 rounded-full bg-gradient-to-br from-purple-600 to-fuchsia-500" />
                      </div>
                      <div className="space-y-2">
                        <p className="text-xl font-semibold text-slate-900">
                          {loadingPhrases[loadingPhraseIndex]}
                        </p>
                        <p className="text-sm text-slate-600">
                          The selected model is analyzing your repository now.
                        </p>
                      </div>
                    </div>
                  </div>
                ) : results ? (
                  noSdgs ? (
                    <div className="py-16">
                      <div className="text-center px-4">
                        <h2 className="text-3xl font-bold text-black">
                          This project does not satisfy any SDG
                        </h2>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* SDG Cards Grid */}
                      <CardGrid sdgPredictions={results.predictions} />

                      {/* Action Buttons */}
                      <div className="flex flex-wrap items-center justify-end gap-3 mt-6">
                        <button
                          onClick={handleDownload}
                          className="cursor-pointer px-4 py-2 bg-white text-purple-600 border border-purple-600 rounded-md hover:bg-purple-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
                        >
                          <span className="flex items-center">Download SDG Analysis Bundle</span>
                        </button>
                        <button
                          onClick={handleChanges}
                          className="cursor-pointer px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors duration-200"
                        >
                          Maybe, we need some edits
                        </button>
                      </div>
                    </>
                  )
                ) : (
                  <RawResults results={results} />
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Edit SDG Predictions Modal */}
      {isModalOpen && results && !noSdgs && (
        <EditModal
          editableResults={editableResults || {}}
          setEditableResults={setEditableResults}
          setIsModalOpen={setIsModalOpen}
          saveEditedResults={saveEditedResults}
        />
      )}
    </div>
  );
};

export default Results;

