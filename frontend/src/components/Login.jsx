import React, { useState } from 'react';

const Login = () => {
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    if (error) setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch('http://localhost:8000/api/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
      });

      const data = await response.json();
      if (response.ok) {
        setSuccess('Login exitoso!');
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('user', JSON.stringify(data.user));
        console.log('Login exitoso:', data);
        // window.location.href = '/dashboard'; // descomenta si usas rutas
      } else {
        setError(data.error || 'Error en el login');
      }
    } catch (err) {
      setError('Error de conexión. Verifica que el servidor esté ejecutándose.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Barra superior */}
      <div className="w-full h-[60px] bg-[#00024A]"></div>

      {/* Cuerpo dividido en dos columnas */}
      <div className="flex flex-1">
        {/* Columna izquierda con imagen */}
        <div className="w-1/2 h-[calc(100vh-60px)] bg-gray-100">
          <img
            src="/logo_sac.png"
            alt="Imagen decorativa"
            className="w-full h-full object-cover"
          />
        </div>

        {/* Columna derecha con formulario */}
        <div className="w-full md:w-1/2 h-[calc(100vh-60px)] bg-gray-100 flex justify-center md:justify-start items-start md:pl-36 pt-20 md:pt-60">
          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            {/* Título */}
            <h2 className="text-[37.43px] font-semibold text-[#00024A] mb-4 font-poppins">
              Login
            </h2>

            {/* Input Usuario */}
            <div className="relative w-[488px] h-[58px]">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                <img src="/login_icon.png" alt="Usuario" className="w-7 h-7 text-gray-400 block" />
              </span>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                placeholder="Usuario"
                className="pl-12 pr-12 py-2 w-full h-full border border-[#E7E7E7] hover:border-[#00024A] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#00024A]
                          text-black font-poppins text-[14.85px] transition-colors duration-200" 
              />
            </div>

            {/* Input Contraseña */}
            <div className="relative w-[488px] h-[58px]">
              <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                <img src="/password_icon.png" alt="Contraseña" className="w-5 h-6 text-gray-400" />
              </span>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                placeholder="Contraseña"
                className="pl-12 pr-12 py-2 w-full h-full border border-[#E7E7E7] hover:border-[#00024A] rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-[#00024A]
                          text-black font-poppins text-[14.85px] transition-colors duration-200"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 focus:outline-none"
              >
                <img
                  src={showPassword ? "/eye_open_icon.png" : "/eye_close_icon.png"}
                  alt="Mostrar/Ocultar"
                  className="w-8 h-8"
                />
              </button>
            </div>

            {/* Botón Ingresar */}
            <div className="mt-6">
              <button
                type="submit"
                className="w-[488px] h-[58px] bg-[#8181A7] text-white font-poppins font-semibold text-[16.29px] rounded-md shadow-sm hover:bg-[#6c6c88] transition-colors"
                disabled={loading}
              >
                {loading ? 'Ingresando...' : 'Ingresar'}
              </button>
            </div>

            {/* Mensaje de error o éxito */}
            {error && <p className="text-red-500 font-medium font-poppins">{error}</p>}
            {success && <p className="text-green-600 font-medium font-poppins">{success}</p>}
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
