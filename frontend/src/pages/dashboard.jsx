import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import SearchBar from "../components/SearchBar";
import FilterDropdown from "../components/FilterDropdown";
import Pagination from "../components/Pagination";
import InventoryTable from "../components/InventoryTable";

const ITEMS_PER_PAGE = 7;

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
            <div
              className="mt-16 flex justify-end"
              style={{ minHeight: "40px" }}
            >
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
