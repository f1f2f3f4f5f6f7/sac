export const logout = (navigate) => {
    localStorage.removeItem('authToken');
    localStorage.removeItem('user');
    navigate('/');
  };
  