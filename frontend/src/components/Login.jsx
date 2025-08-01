import React, { useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Grid,
  InputAdornment,
  IconButton,
  Paper,
  TextField,
  Typography,
  Alert
} from '@mui/material';
import { Visibility, VisibilityOff } from '@mui/icons-material';
import AccountCircle from '@mui/icons-material/AccountCircle';
import VpnKeyIcon from '@mui/icons-material/VpnKey';

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
    <Grid container component="main" sx={{ height: '100vh', backgroundColor: '#f5f6fa' }}>
      <Grid item xs={12} md={6} sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <Box textAlign="center">
          <Box sx={{ mb: 2, width: 70, height: 70, bgcolor: '#001f4d', borderRadius: 2, mx: 'auto', position: 'relative' }}>
            <Box sx={{ position: 'absolute', top: 3, left: 3, right: 3, bottom: 3, border: '2px solid white', borderRadius: 1 }} />
            {/* Puedes agregar más elementos decorativos si deseas */}
          </Box>
          <Typography variant="h3" sx={{ color: '#001f4d', fontWeight: 'bold' }}>SAC</Typography>
        </Box>
      </Grid>

      <Grid item xs={12} md={6} component={Paper} elevation={6} square sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Box sx={{ width: '80%', maxWidth: 400 }}>
          <Typography variant="h4" sx={{ mb: 3, fontWeight: 'bold' }}>Login</Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}
          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              name="username"
              label="Username"
              value={formData.username}
              onChange={handleInputChange}
              margin="normal"
              required
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <AccountCircle color="primary" />
                  </InputAdornment>
                )
              }}
            />
            <TextField
              fullWidth
              name="password"
              label="Contraseña"
              type={showPassword ? 'text' : 'password'}
              value={formData.password}
              onChange={handleInputChange}
              margin="normal"
              required
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <VpnKeyIcon color="primary" />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton onClick={() => setShowPassword((prev) => !prev)}>
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                )
              }}
            />
            <Box textAlign="right" sx={{ mb: 2 }}>
              <Typography variant="body2" color="primary" sx={{ cursor: 'pointer' }}>
                Forgot Password?
              </Typography>
            </Box>
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ bgcolor: '#8576FF', '&:hover': { bgcolor: '#6a5acd' } }}
              disabled={loading}
            >
              {loading ? <CircularProgress size={24} sx={{ color: 'white' }} /> : 'Login'}
            </Button>
          </form>
        </Box>
      </Grid>
    </Grid>
  );
};

export default Login;
