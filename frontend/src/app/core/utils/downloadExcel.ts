export function downLoadExcel(blob: Blob) {
  const urlArchivo = window.URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = urlArchivo;

  link.download = `Solicitud_Baja_${new Date().getTime()}.xlsx`;

  link.target = '_blank';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  window.URL.revokeObjectURL(urlArchivo);
}
