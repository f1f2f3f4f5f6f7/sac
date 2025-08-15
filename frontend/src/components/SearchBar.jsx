import React from "react";

const SearchBar = ({ searchTerm, setSearchTerm }) => {
    return (
      <div className="mb-4 flex items-center justify-between w-full max-w-[1190px] ml-auto px-4 sm:px-0">
        <div className="relative w-full max-w-[800px] h-[43px]">
          <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
            <img
              src="/search_icon.png"
              alt="Icono de búsqueda"
              className="w-5 h-5 text-gray-400 block"
            />
          </span>
          <input
            type="text"
            placeholder="Buscar..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="pl-12 pr-3 py-2 w-full h-full border border-[#E7E7E7] hover:border-[#00024A] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#00024A]
            text-black font-poppins text-[12px] transition-colors duration-200"
            aria-label="Buscar en el inventario"
          />
        </div>
  
        <button
          type="button"
          className="ml-4 w-[50px] h-[43px] bg-[#8181A7] rounded-md flex items-center justify-center"
          aria-label="Botón ingresar"
        >
          <img
            src="/download_icon.png"
            alt="Descargar"
            className="max-h-[70%] max-w-full object-contain"
          />
        </button>
      </div>
    );
  };

  export default SearchBar;