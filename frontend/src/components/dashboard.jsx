import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { logout } from "../utils/logout";

const Dashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(false);

  const handleNavigate = (path) => {
    navigate(path);
  };

  useEffect(() => {
    // Simulación de datos desde la API
    const fetchData = async () => {
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
      ];
      setData(mockData);
    };

    fetchData();
  }, []);

  // Filtrar datos en tiempo real - optimizado
  const term = searchTerm.toLowerCase().trim();

  const filteredData = data.filter((item) =>
    ["codigo", "elemento", "estado", "serie", "valor", "ubicacion"].some(
      (key) => item[key]?.toLowerCase().includes(term)
    )
  );

  return (
    <div className="min-h-screen flex flex-col font-poppins">
      {/* Barra superior */}
      <div className="w-full h-[60px] bg-[#00024A] flex items-center px-6 gap-6 justify-between">
        {/* Sección izquierda */}
        <div className="flex items-center gap-6">
          <div className="w-6" />
          <div className="w-[1px] h-[39px] bg-white" />
          <button
            onClick={() => handleNavigate("/inventario")}
            className="text-white text-[20px] font-light hover:underline"
          >
            Mi Inventario
          </button>
          <button
            onClick={() => handleNavigate("/busqueda")}
            className="text-white text-[20px] font-light hover:underline"
          >
            Búsqueda
          </button>
          <button
            onClick={() => handleNavigate("/peticion")}
            className="text-white text-[20px] font-light hover:underline"
          >
            Petición
          </button>
        </div>

        {/* Sección derecha: usuario */}
        <div className="relative group">
          <div className="flex items-center gap-2 px-4 py-2 bg-white rounded-full cursor-pointer">
            <div className="w-9 h-9 rounded-full bg-[#8181A7] flex items-center justify-center overflow-hidden">
              <img
                src="/user_icon_2.png"
                alt="Avatar de usuario"
                className="w-6 h-6 object-cover"
              />
            </div>
            <span className="text-black font-light">Juan</span>
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

          {/* Menú desplegable */}
          <div className="absolute right-0 mt-2 w-40 bg-white text-black rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10">
            <button
              onClick={() => handleNavigate("/mi_cuenta")}
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
              onClick={() => logout(navigate)}
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
      </div>

      {/* Contenido del dashboard */}
      <div className="flex flex-1 bg-gray-100">
        {/* Espacio para filtros */}
        <div className="w-[250px] bg-gray-100 p-4 hidden">FILTROS</div>

        {/* Contenedor principal */}
        <div className="flex-1 pl-40 pr-[200px] py-20">
          {/* Caja de búsqueda alineada con la tabla */}
          <div className="mb-4 flex items-center justify-between w-[1300px] ml-auto">
            <div className="relative w-[716px] h-[43px]">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3">
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

            {/* Botón con imagen en blanco */}
            <button
              type="button"
              className="ml-4 w-[200px] h-[43px] bg-white rounded-md flex items-center justify-center"
              aria-label="Botón ingresar"
            >
              <img
                src="/icono_ingresar.png"
                alt="Descargar"
                className="max-h-[70%] max-w-full object-contain"
              />
            </button>
          </div>

          {/* Contenedor tabla */}
          <div className="bg-white rounded-lg shadow overflow-x-auto w-[1300px] ml-auto">
            <table className="text-left border-collapse w-[1300px]">
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
                {filteredData.map((item) => (
                  <tr
                    key={item.codigo}
                    className="border-b font-poppins text-[14px] text-[#000000]"
                  >
                    <td className="px-4 py-3">{item.codigo}</td>
                    <td className="px-4 py-3">{item.elemento}</td>
                    <td className="px-4 py-3">
                      <span
                        className={
                          item.estado === "Funcional"
                            ? "text-green-500"
                            : item.estado === "No Funcional"
                            ? "text-red-500"
                            : item.estado === "Mantenimiento"
                            ? "text-yellow-500"
                            : "text-blue-500"
                        }
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
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
