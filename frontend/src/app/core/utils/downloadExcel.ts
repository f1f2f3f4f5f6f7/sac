export function downLoadExcel(blob: Blob, tramite: string) {
  const urlArchivo = window.URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = urlArchivo;

  link.download = `${tramite}_${new Date().toISOString().split('T')[0]}.xlsx`;

  link.target = '_blank';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  window.URL.revokeObjectURL(urlArchivo);
}
