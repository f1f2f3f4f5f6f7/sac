import React, { useState, useEffect } from "react";
import { ChevronDown, ChevronUp, Filter } from "lucide-react";

const FilterDropdown = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [filters, setFilters] = useState({
      mayores: false,
      menores: false,
    });
  
    const toggleDropdown = () => setIsOpen(!isOpen);
    const toggleFilter = (key) => {
      setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
    };
  
    return (
      <div className="w-full max-w-[220px] ml-4">
        <div
          className="flex justify-between items-center bg-white rounded-lg px-4 py-2 shadow-sm border border-gray-200 cursor-pointer select-none hover:shadow-md transition-all duration-200"
          onClick={toggleDropdown}
        >
          <span className="font-medium text-gray-800">Elementos</span>
          {isOpen ? (
            <ChevronUp size={18} className="text-gray-600" />
          ) : (
            <ChevronDown size={18} className="text-gray-600" />
          )}
        </div>
  
        <div
          className={`overflow-hidden transition-all duration-300 ease-in-out ${
            isOpen ? "max-h-40 opacity-100 mt-1" : "max-h-0 opacity-0"
          }`}
        >
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm px-4 py-3 space-y-3">
            <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded-md">
              <input
                type="checkbox"
                checked={filters.mayores}
                onChange={() => toggleFilter("mayores")}
                className="w-4 h-4 accent-blue-500"
              />
              <span className="text-gray-700">Mayores</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded-md">
              <input
                type="checkbox"
                checked={filters.menores}
                onChange={() => toggleFilter("menores")}
                className="w-4 h-4 accent-blue-500"
              />
              <span className="text-gray-700">Menores</span>
            </label>
          </div>
        </div>
      </div>
    );
  };

  export default FilterDropdown;