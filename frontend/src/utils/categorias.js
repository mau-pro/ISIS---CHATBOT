/**
 * utils/categorias.js
 * ---------------------
 * Las 4 categorías con las que el admin clasifica un documento al subirlo.
 * `value` coincide con el Enum DocumentCategory del backend. Los colores
 * (clase cat-*) se definen en admin.css y repiten los de la portada:
 * horarios violeta, docentes rosa, avisos cian, otros ámbar.
 */

export const CATEGORIAS = [
  { value: "horario", label: "Horarios", icono: "calendar_month", ayuda: "Aulas, días y grupos" },
  { value: "docentes", label: "Docentes", icono: "co_present", ayuda: "Materias asignadas" },
  { value: "aviso", label: "Avisos y comunicados", icono: "campaign", ayuda: "Convocatorias y noticias" },
  { value: "otro", label: "Otros", icono: "folder_open", ayuda: "Cualquier otro documento" },
];

export function infoCategoria(value) {
  return CATEGORIAS.find((c) => c.value === value) || CATEGORIAS[CATEGORIAS.length - 1];
}
