import React from "react";
import { IoIosInformationCircleOutline } from "react-icons/io";
import { Recommendation } from "@/types/main";

interface NoSdgPageProps {
  recommendation?: Recommendation;
}

const reasonMessages: Record<string, string> = {
  text_too_short: "Your project description and README are too short to assess SDG relevance.",
  no_sdg_signals: "No SDG-relevant signals were found in the provided text.",
  heavily_technical: "The description appears heavily technical without clear real-world impact signals.",
  threshold_too_high: "The SDG relevance threshold may be too high for the available content.",
  signals_present_but_low_similarity: "SDG-relevant signals were found, but similarity scores are low.",
};

const reasonDescriptions: Record<string, string> = {
  text_too_short: "Expand your project description to at least 20-30 words including what problem your project solves.",
  no_sdg_signals: "Make your description more elaborate and less technical. Focus on what the project does, who benefits, and the real-world impact.",
  heavily_technical: "Rewrite the description in non-technical terms. Remove mentions of programming languages, frameworks, and libraries. Focus on the problem your project addresses.",
  threshold_too_high: "Try providing more detailed description or lowering the SDG relevance threshold.",
  signals_present_but_low_similarity: "Add more specific details about your project's impact, beneficiaries, and geographic or sector context.",
};

const NoSdgPage: React.FC<NoSdgPageProps> = ({ recommendation }) => {
  const [openModal, setOpenModal] = React.useState(false);

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const reason = recommendation
    ? reasonMessages[recommendation.reason] ||
      reasonDescriptions[recommendation.reason] ||
      "We couldn't find SDG matches above the relevance threshold."
    : "We couldn't find SDG matches above the relevance threshold for the provided repository/description.";

  const suggestions = recommendation
    ? recommendation.suggestions.map((s, i) => (
        <li key={i} className="mb-2 flex items-start">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4 flex-shrink-0 text-purple-600 mt-1"
            viewBox="0 0 24 24"
          >
            <path
              d="M9 12l2 2 4-4-4-4L14 2l4 4L9 12z"
            />
          </svg>
          <span className="ml-3 text-gray-600">{s}</span>
        </li>
      ))
    : [
        "Expand your project description to at least 20-30 words",
        "Include what problem your project solves",
        "Mention who benefits from your project",
        "Add geographic or sector context (e.g., 'rural farmers', 'low-income countries')",
      ];

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br">
      <div
        className="text-center space-y-6 max-w-xl px-6"
        onClick={() => setOpenModal(true)}
      >
        <h1 className="text-3xl sm:text-4xl font-bold text-black">
          This project does not satisfy any SDG
        </h1>
        <p className="text-gray-600 text-lg">
          {reason}
        </p>

        {suggestions.length > 0 && (
          <div className="bg-white rounded-lg p-6 max-w-lg mx-auto shadow-lg">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">
              Possible solutions:
            </h3>
            <ul className="space-y-3 text-left text-gray-700">
              {suggestions}
            </ul>
          </div>
        )}

        <button
          onClick={() => setOpenModal(true)}
          className="mt-4 px-4 py-2 bg-purple-700 text-white rounded-md hover:bg-purple-800 transition-colors duration-200"
        >
          Show detailed guidance
        </button>
      </div>

      {/* Modal with copy functionality */}
      {openModal && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-zindex flex items-center justify-center z-50"
        >
          <div
            className="bg-white rounded-lg p-8 max-w-md w-full shadow-2xl transform scale-95"
            role="dialog"
            aria-modal="true"
          >
            <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center">
              {recommendation
                ? reasonDescriptions[recommendation.reason]
                : "Guidance for SDG Classification"}
            </h3>

            <p className="text-gray-600 mb-8 line-clamp-6">
              {reason}
            </p>

            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-500 mb-2">
                Copy guidance for pasting into your project description:
              </p>
              <textarea
                readOnly
                className="w-full p-3 rounded border border-gray-300 focus:border-purple-500 focus:outline-none"
                onClick={e => handleCopy(e.currentTarget.value)}
              >
                {recommendation
                  ? reasonDescriptions[recommendation.reason]
                  : ""}
              </textarea>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setOpenModal(false)}
                className="flex-1 px-4 py-2 bg-gray-200 rounded-md hover:bg-gray-300 transition-colors text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NoSdgPage;