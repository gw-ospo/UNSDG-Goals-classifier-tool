import React, { useState } from "react";
import { ImCross } from "react-icons/im";
import { RiDeleteBin5Line } from "react-icons/ri";
import { IoAdd } from "react-icons/io5";
import SDG from "./sdg";
import { SDGValue, EditModalProps } from "@/types/main";

/*
EditModal Component
- Modal interface for editing SDG predictions
- Allows adding new SDG goals and adjusting confidence scores
- Displays current editable SDG predictions with options to remove or modify
- Save changes or cancel edits
*/

const EditModal: React.FC<EditModalProps> = ({
  editableResults,
  setEditableResults,
  setIsModalOpen,
  saveEditedResults,
}) => {
  const parseSdgFromString = (value: string) => {
    const number = (value.match(/SDG\s*(\d+)/i) || value.match(/^(\d+)/))?.[1] ?? "";
    const name = value.replace(/^SDG\s*\d+\s*:?\s*/i, "").trim() || value;
    return { number, name };
  };

  const getSdgNumber = (sdgKey: string, value: SDGValue) => {
    if (typeof value.sdg === "string") {
      return parseSdgFromString(value.sdg).number || sdgKey;
    }
    return value?.sdg?.code ?? parseSdgFromString(sdgKey).number ?? sdgKey;
  };

  const getSdgName = (sdgKey: string, value: SDGValue) => {
    if (typeof value.sdg === "string") {
      return parseSdgFromString(value.sdg).name;
    }
    return value?.sdg?.name ?? value?.sdg?.label ?? sdgKey;
  };

  const [showAddForm, setShowAddForm] = useState(false);
  const [newSDGNumber, setNewSDGNumber] = useState("");
  const [newSDGName, setNewSDGName] = useState("");
  const [newSDGScore, setNewSDGScore] = useState(1.0);

  const removeSDG = (sdgKey: string) => {
    setEditableResults((prev) => {
      const cur = prev[sdgKey] || {};
      return {
        ...prev,
        [sdgKey]: { ...(cur as SDGValue), prediction: 0 },
      };
    });
  };

  console.log("Editable Results:", editableResults);

  const addNewSDG = () => {
    if (newSDGNumber && newSDGName) {
      const sdgKey = Object.keys(editableResults).length;
      const exists = Object.values(editableResults).some(
        (value) => String(getSdgNumber("", value)) === String(newSDGNumber),
      );

      if (exists) {
        alert("This SDG already exists!");
        return;
      }

      const newValue: SDGValue = {
        prediction: newSDGScore,
        sdg: {
          "@type": "sdg",
          code: String(newSDGNumber),
          icon: `https://aurora-sdg-classifier.uni-due.de/resources/sdg_icon_${newSDGNumber}.png`,
          id: `http://metadata.un.org/sdg/${newSDGNumber}`,
          name: newSDGName,
          label: `Goal ${newSDGNumber}`,
          type: "Goal",
        },
      };

      setEditableResults((prev) => ({
        ...prev,
        [sdgKey]: newValue,
      }));

      setNewSDGNumber("");
      setNewSDGName("");
      setNewSDGScore(1.0);
      setShowAddForm(false);
    }
  };

  const cancelAddSDG = () => {
    setNewSDGNumber("");
    setNewSDGName("");
    setNewSDGScore(1.0);
    setShowAddForm(false);
  };

  const handleSDGSelection = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedNumber = e.target.value;
    setNewSDGNumber(selectedNumber);

    if (selectedNumber) {
      const sdgNumber = parseInt(selectedNumber) as keyof typeof SDG;
      if (SDG[sdgNumber]) {
        setNewSDGName(SDG[sdgNumber]);
      }
    } else {
      setNewSDGName("");
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        <div className="bg-purple-600 text-white p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold">Edit SDG Predictions</h2>
            <button
              onClick={() => setIsModalOpen(false)}
              className="text-white hover:text-gray-200 transition-colors"
            >
              <ImCross />
            </button>
          </div>
        </div>

        <div className="p-6 overflow-y-auto max-h-[60vh]">
          <div className="flex justify-between items-center mb-4">
            <p className="text-gray-600">
              Add the SDG&apos;s that are highly relevant to your project
            </p>
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="flex items-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm"
            >
              <IoAdd className="w-4 h-4" />
              Add New SDG
            </button>
          </div>

          {showAddForm && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mb-4">
              <h4 className="font-semibold text-gray-800 mb-3">
                Add New SDG Goal
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    SDG Number
                  </label>
                  <select
                    value={newSDGNumber}
                    onChange={(e) => {
                      handleSDGSelection(e);
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value="">Select SDG Number</option>
                    {Array.from({ length: 17 }, (_, i) => i + 1).map((num) => (
                      <option key={num} value={num}>
                        SDG {num}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    SDG Name
                  </label>
                  <input
                    type="text"
                    disabled
                    value={newSDGName}
                    onChange={(e) => setNewSDGName(e.target.value)}
                    placeholder="SDG Goal Name"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Confidence Score
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={newSDGScore}
                    disabled
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 mt-4">
                <button
                  onClick={cancelAddSDG}
                  className="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors text-sm"
                >
                  Cancel
                </button>
                <button
                  onClick={addNewSDG}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors text-sm"
                >
                  Add SDG
                </button>
              </div>
            </div>
          )}

          <div className="space-y-4">
            {Object.entries(editableResults)
              .sort(
                ([, a], [, b]) =>
                  Number(b.prediction ?? 0) - Number(a.prediction ?? 0),
              )
              .map(([sdgKey, value]) => {
                const confidence = value.prediction ?? 0;
                const sdgNumber = getSdgNumber(sdgKey, value);
                const sdgName = getSdgName(sdgKey, value);

                return (
                  <div
                    key={sdgKey}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                        {sdgNumber}
                      </div>

                      <div className="flex-1 min-w-0">
                        <h4 className="font-semibold text-gray-800 text-sm">
                          SDG {sdgNumber}
                        </h4>
                        <p
                          className="text-gray-600 text-sm truncate"
                          title={sdgName}
                        >
                          {sdgName}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <label className="text-sm text-gray-600 font-medium">
                          Score:
                        </label>
                        <input
                          type="number"
                          min="0"
                          max="1"
                          step="0.001"
                          value={confidence}
                          disabled
                          className="w-20 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                        />
                        <span className="text-sm text-gray-500">
                          ({Math.round(Number(confidence) * 100)}%)
                        </span>
                        <button
                          onClick={() => removeSDG(sdgKey)}
                          className="ml-2 text-red-500 hover:text-red-700 transition-colors"
                          title="Set SDG score to 0"
                        >
                          <RiDeleteBin5Line />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 ml-16">
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                          style={{
                            width: `${Math.round(Number(confidence) * 100)}%`,
                          }}
                        ></div>
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>

        <div className="bg-gray-50 px-6 py-4 flex justify-end gap-3">
          <button
            onClick={() => setIsModalOpen(false)}
            className="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={saveEditedResults}
            className="px-6 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
};

export default EditModal;
