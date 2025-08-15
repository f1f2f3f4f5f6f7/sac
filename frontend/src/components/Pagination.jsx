import React from "react";


const ITEMS_PER_PAGE = 7;


const Pagination = ({ totalItems, currentPage, onPageChange }) => {
    const totalPages = Math.ceil(totalItems / ITEMS_PER_PAGE);
  
    if (totalPages === 1) return null; // No mostrar paginación si solo hay 1 página
  
    // Generar array con números de página [1, 2, 3, ..., totalPages]
    const pages = Array.from({ length: totalPages }, (_, i) => i + 1);
  
    return (
      <nav
        className="flex justify-end space-x-2 my-4 w-full max-w-[1190px] ml-auto px-4 sm:px-0"
        aria-label="Paginación"
      >
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="w-10 h-7 flex items-center justify-center rounded border disabled:opacity-50 transition-colors duration-150 hover:bg-gray-200"
          aria-label="Primera página"
        >
          <img
            src="/doble_flecha_atras_icon.png"
            alt="doble_flecha_atras"
            className="max-h-[40%] max-w-[40%] object-contain"
          />
        </button>
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="w-10 h-7 flex items-center justify-center rounded border disabled:opacity-50 transition-colors duration-150 hover:bg-gray-200"
          aria-label="Página anterior"
        >
          <img
            src="/flecha_atras_icon.png"
            alt="flecha_atras"
            className="max-h-[40%] max-w-[40%] object-contain"
          />
        </button>
  
        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`w-10 h-7 rounded border flex items-center justify-center text-sm font-poppins text-[13px] font-medium transition-colors duration-150 ${
              page === currentPage
                ? "bg-[#8181A7] text-[#FFFFFF]"
                : "text-[#282828] hover:bg-gray-200 cursor-pointer"
            }`}
            aria-current={page === currentPage ? "page" : undefined}
          >
            {page}
          </button>
        ))}
  
        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="w-10 h-7 flex items-center justify-center rounded border disabled:opacity-50 transition-colors duration-150 hover:bg-gray-200"
          aria-label="Página siguiente"
        >
          <img
            src="/flecha_adelante_icon.png"
            alt="flecha_adelante"
            className="max-h-[40%] max-w-[40%] object-contain"
          />
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="w-10 h-7 flex items-center justify-center rounded border disabled:opacity-50 transition-colors duration-150 hover:bg-gray-200"
          aria-label="Última página"
        >
          <img
            src="/doble_flecha_adelante_icon.png"
            alt="doble_flecha_adelante"
            className="max-h-[40%] max-w-[40%] object-contain"
          />
        </button>
      </nav>
    );
  };
  

  export default Pagination;