import React from "react";

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

  export default InventoryTable;