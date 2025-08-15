import React from "react";
import UserMenu from "../components/UserMenu"

const Navbar = ({ onNavigate }) => {
    return (
      <div className="w-full h-16 bg-[#00024A] flex items-center px-6 gap-6 justify-between">
        <div className="flex items-center gap-6">
          <div className="w-6" />
          <div className="w-px h-[39px] bg-white" />
          <button
            onClick={() => onNavigate("/inventario")}
            className="text-white text-lg font-light hover:underline"
          >
            Mi Inventario
          </button>
          <button
            onClick={() => onNavigate("/busqueda")}
            className="text-white text-lg font-light hover:underline"
          >
            Búsqueda
          </button>
          <button
            onClick={() => onNavigate("/peticion")}
            className="text-white text-lg font-light hover:underline"
          >
            Petición
          </button>
        </div>
  
        <UserMenu onNavigate={onNavigate} />
      </div>
    );
  };

  export default Navbar;