import React from "react";
import { SDGValue, CardGridProps } from "@/types/main";

/*
CardGrid Component
- Displays a grid of SDG cards based on predictions
- Each card shows SDG number, name, confidence score, and a progress bar
*/

type SDGCardProps = {
  sdgNumber: string;
  sdgName: string;
  confidence: number;
};

const SDGCard = ({ sdgNumber, sdgName, confidence }: SDGCardProps) => {

  const confidenceScore = Number(confidence);
  const confidencePercentage = Math.round(confidenceScore * 100);

  let confidenceLevel = "";
  let colorClasses = "";
  let bgColor = "";

  if (confidenceScore >= 0.8) {
    confidenceLevel = "High";
    colorClasses = "text-green-700 border-green-300";
    bgColor = "bg-green-50";
  } else if (confidenceScore >= 0.6) {
    confidenceLevel = "Medium";
    colorClasses = "text-yellow-700 border-yellow-300";
    bgColor = "bg-yellow-50";
  } else {
    confidenceLevel = "Low";
    colorClasses = "text-red-700 border-red-300";
    bgColor = "bg-red-50";
  }

  return (
    <div
      className={`${bgColor} ${colorClasses} border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow duration-200`}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold text-lg">
            {sdgNumber}
          </div>
          <div>
            <h4 className="font-semibold text-gray-800 text-sm">
              SDG {sdgNumber}
            </h4>
            <span
              className={`text-xs px-2 py-1 rounded-full font-medium ${
                confidenceLevel === "High"
                  ? "bg-green-100 text-green-800"
                  : confidenceLevel === "Medium"
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-red-100 text-red-800"
              }`}
            >
              {confidenceLevel} Match
            </span>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-gray-800">
            {confidencePercentage}%
          </div>
        </div>
      </div>

      <h5 className="font-medium text-gray-700 mb-3 leading-tight line-clamp-2">
        {sdgName}
      </h5>

      <div className="space-y-2">
        <div className="flex justify-between text-sm text-gray-600">
          <span>Confidence Score</span>
          <span>{confidenceScore.toFixed(3)}</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              confidenceLevel === "High"
                ? "bg-green-500"
                : confidenceLevel === "Medium"
                  ? "bg-yellow-500"
                  : "bg-red-500"
            }`}
            style={{ width: `${confidencePercentage}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
};

const CardGrid = ({ sdgPredictions }: CardGridProps) => {
  const predictionsArray: Array<SDGPrediction & { sourceKey: string }> =
    Array.isArray(sdgPredictions)
      ? sdgPredictions.map((item, index) => ({
          ...item,
          sourceKey: String(index),
        }))
      : (Object.entries(sdgPredictions ?? {}).map(([sourceKey, item]) => {
          if (typeof item === "number") {
            return { prediction: item, sourceKey };
          }
          if (item && typeof item === "object" && "prediction" in item) {
            return { ...item, sourceKey };
          }
          return { prediction: 0, sourceKey };
        })
          .filter((item): item is SDGPrediction & { sourceKey: string } => {
            return item.prediction > 0;
          }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {predictionsArray
        .sort((a, b) => b.prediction - a.prediction)
        .map((item, index) => {
          const fallbackNumberFromKey = item.sourceKey.match(/\d+/)?.[0];
          const sdgNumber =
            typeof item.sdg === "string"
              ? item.sdg.match(/\d+/)?.[0] ||
                fallbackNumberFromKey ||
                (index + 1).toString()
              : item.sdg?.code || fallbackNumberFromKey || (index + 1).toString();
          const sdgName =
            typeof item.sdg === "string"
              ? item.sdg.replace(/^SDG\s*\d+\s*:?\s*/i, "").trim() || item.sdg
              : item.sdg?.name ||
                item.sdg?.label ||
                item.sourceKey.replace(/^SDG\s*\d+\s*:?\s*/i, "").trim() ||
                `SDG ${sdgNumber}`;

          return (
            <SDGCard
              key={`${sdgNumber}-${index}`}
              sdgNumber={sdgNumber}
              sdgName={sdgName}
              confidence={item.prediction}
            />
          );
        })}
    </div>
  );
};

export default CardGrid;
