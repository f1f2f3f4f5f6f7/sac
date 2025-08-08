import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { logout } from "../utils/logout";

const ITEMS_PER_PAGE = 7;

// Componente paginador
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

// Componente Navbar con los botones de navegación y menú usuario
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

// Menú desplegable de usuario
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

// Barra de búsqueda con ícono y botón de descarga
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
    <div className="max-w-[200px] ml-4">
      <div
        className="flex justify-between items-center bg-white rounded-md px-4 py-2 shadow cursor-pointer select-none"
        onClick={toggleDropdown}
      >
        <span className="font-semibold text-gray-800">Elementos</span>
        <span className="text-gray-600 text-xl font-bold">{isOpen ? "-" : "+"}</span>
      </div>

      {isOpen && (
        <div className="bg-white rounded-b-md border border-t-0 shadow px-4 py-2 space-y-2">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.mayores}
              onChange={() => toggleFilter("mayores")}
              className="w-4 h-4"
            />
            <span>Mayores</span>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filters.menores}
              onChange={() => toggleFilter("menores")}
              className="w-4 h-4"
            />
            <span>Menores</span>
          </label>
        </div>
      )}
    </div>
  );
};

// Tabla del inventario
const InventoryTable = ({ data }) => {
  const estadoColor = {
    Funcional: "text-green-500",
    "No Funcional": "text-red-500",
    Mantenimiento: "text-yellow-500",
    default: "text-blue-500",
  };

  return (
    <div className="bg-white rounded-lg shadow overflow-x-auto w-full max-w-[1190px] ml-auto">
      <table className="text-left border-collapse w-full min-w-[700px]">
        <thead className="bg-gray-50">
          <tr>
            {[
              "Código",
              "Elemento",
              "Estado",
              "Serie",
              "Valor",
              "Ubicación",
              "Acciones",
            ].map((header) => (
              <th
                key={header}
                className="px-4 py-3 text-[#6C6C6C] font-poppins font-normal text-[13px]"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={item.codigo}
              className="border-b font-poppins text-[14px] text-[#1E1E1E]"
            >
              <td className="px-4 py-3">{item.codigo}</td>
              <td className="px-4 py-3">{item.elemento}</td>
              <td className="px-4 py-3">
                <span
                  className={estadoColor[item.estado] || estadoColor.default}
                >
                  {item.estado}
                </span>
              </td>
              <td className="px-4 py-3">{item.serie}</td>
              <td className="px-4 py-3">{item.valor}</td>
              <td className="px-4 py-3">{item.ubicacion}</td>
              <td className="px-4 py-3 flex gap-4">
                <button aria-label="Ver detalles">
                  <img
                    src="/info_icon.png"
                    alt="Icono ver detalles"
                    className="w-10 h-10"
                  />
                </button>
                {item.estado !== "En Prestamo" &&
                  item.estado !== "Prestado" && (
                    <button aria-label="Editar">
                      <img
                        src="/edit_icon.png"
                        alt="Icono editar"
                        className="w-10 h-10"
                      />
                    </button>
                  )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

const Dashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");

  // Estado de paginación
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    const fetchData = async () => {
      // Aquí podrías reemplazar por llamada real a API
      const mockData = [
        {
          codigo: "A342_24442MC",
          elemento: "ZAV2_24442MC",
          estado: "No Funcional",
          serie: "Heavy Weight",
          valor: "Feb 05, 2022",
          ubicacion: "Pickup trucks",
        },
        {
          codigo: "BC342_24442MC",
          elemento: "N/A",
          estado: "Funcional",
          serie: "Heavy Weight",
          valor: "Aug 12, 2023",
          ubicacion: "Garbage Trucks",
        },
        {
          codigo: "CC21_24442MC",
          elemento: "ZAV2_24442MC",
          estado: "En Prestamo",
          serie: "Heavy Weight",
          valor: "Oct 22, 2021",
          ubicacion: "Fords",
        },
        {
          codigo: "ZAV2_24442MC",
          elemento: "N/A",
          estado: "Prestado",
          serie: "Light Weight",
          valor: "Dec 04, 2020",
          ubicacion: "Nissan",
        },
        {
          codigo: "D554_24442MC",
          elemento: "ZAV2_24442MC",
          estado: "Funcional",
          serie: "Heavy Weight",
          valor: "Jan 10, 2024",
          ubicacion: "Trucks",
        },
        {
          codigo: "E332_24442MC",
          elemento: "N/A",
          estado: "Mantenimiento",
          serie: "Light Weight",
          valor: "Mar 14, 2023",
          ubicacion: "Vans",
        },
        {
          codigo: "F112_24442MC",
          elemento: "ZAV2_24442MC",
          estado: "Funcional",
          serie: "Heavy Weight",
          valor: "Nov 05, 2021",
          ubicacion: "Buses",
        },
        {
          codigo: "G224_24442MC",
          elemento: "N/A",
          estado: "No Funcional",
          serie: "Light Weight",
          valor: "Jul 21, 2022",
          ubicacion: "Cars",
        },
        {
          codigo: "H992_24442MC",
          elemento: "ZAV2_24442MC",
          estado: "Funcional",
          serie: "Heavy Weight",
          valor: "Sep 17, 2020",
          ubicacion: "Sedans",
        },
        
        // agrega más para probar paginación
      ];
      setData(mockData);
    };

    fetchData();
  }, []);

  const term = searchTerm.toLowerCase().trim();

  // Filtrar datos según búsqueda
  const filteredData = data.filter((item) =>
    ["codigo", "elemento", "estado", "serie", "valor", "ubicacion"].some(
      (key) => item[key]?.toLowerCase().includes(term)
    )
  );

  // Calcular datos para la página actual
  const totalItems = filteredData.length;
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE;
  const currentItems = filteredData.slice(
    startIndex,
    startIndex + ITEMS_PER_PAGE
  );

  const handleNavigate = (path) => {
    navigate(path);
  };

  // Cuando cambias de página, haces scroll al inicio de la tabla (opcional)
  const handlePageChange = (page) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="min-h-screen flex flex-col font-poppins">
      <Navbar onNavigate={handleNavigate} />

      <div className="flex flex-1 bg-gray-100">
  {/* Sidebar filtro fijo a la izquierda */}
  <aside className="w-[250px] p-6 bg-gray-100 ml-[170px] py-20 overflow-x-auto">
  <FilterDropdown />
</aside>


  {/* Contenido principal a la derecha */}
  <main className="flex-1 px-8 py-20 max-w-full overflow-x-auto pr-[250px]">
    <SearchBar searchTerm={searchTerm} setSearchTerm={setSearchTerm} />

    <div className="max-w-[1190px] ml-auto">
      <InventoryTable data={currentItems} />
      <div className="mt-16 flex justify-end" style={{ minHeight: "40px" }}>
        <Pagination
          totalItems={totalItems}
          currentPage={currentPage}
          onPageChange={handlePageChange}
        />
      </div>
    </div>
  </main>
</div>


    </div>
  );
};

export default Dashboard;
