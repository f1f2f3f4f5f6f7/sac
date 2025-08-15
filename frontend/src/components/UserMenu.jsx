import React from "react";
import { logout } from "../utils/logout";

const UserMenu = ({ onNavigate }) => {
    return (
      <div className="relative group">
        <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full cursor-pointer select-none">
          <div className="w-9 h-9 rounded-full bg-[#8181A7] flex items-center justify-center overflow-hidden">
            <img
              src="/user_icon_2.png"
              alt="Avatar de usuario"
              className="w-6 h-6 object-cover"
            />
          </div>
          <span className="text-black font-light select-text">Juan</span>
          <svg
            className="w-4 h-4 text-black"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
  
        <div className="absolute right-0 mt-2 w-40 bg-white text-black rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
          <button
            onClick={() => onNavigate("/mi_cuenta")}
            className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2"
            aria-label="Ir a Mi Cuenta"
          >
            <img
              src="/settings_icon.png"
              alt="Icono de configuración"
              className="w-4 h-4"
            />
            Mi Cuenta
          </button>
          <button
            onClick={() => logout(onNavigate)}
            className="w-full text-left px-4 py-2 hover:bg-gray-100 flex items-center gap-2"
            aria-label="Cerrar sesión"
          >
            <img
              src="/logout_icon.png"
              alt="Icono de cerrar sesión"
              className="w-4 h-4"
            />
            Logout
          </button>
        </div>
      </div>
    );
  };

  export default UserMenu;