/* ==============================================================================
   PROYECTO: MEGASEG SEGURIDAD INTEGRAL - SCRIPT DE INTERACTIVIDAD (JS)
   Arquitectura Inspirada en NexoDigital: Búsqueda en vivo, filtros, WhatsApp
   y Control Interactivo "Ver Más / Ver Menos Detalles"
   ============================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // --------------------------------------------------------------------------
    // 1. MOTOR DE BÚSQUEDA Y FILTRADO MULTICRITERIO EN SERVICIOS.HTML
    // --------------------------------------------------------------------------
    const formFiltros = document.getElementById("formFiltrosCatalogo");
    const inputBuscador = document.getElementById("buscadorServicios");
    const btnLimpiar = document.getElementById("btnLimpiarBusqueda");
    const selectCategoria = document.getElementById("filtroCategoria");
    const selectDisponibilidad = document.getElementById("filtroDisponibilidad");
    const selectOrdenar = document.getElementById("ordenarServicios");
    const chipsCategoria = document.querySelectorAll(".filtro-chip");
    const contenedorCards = document.getElementById("contenedorServicios");
    const sinResultados = document.getElementById("sinResultados");
    const contadorVisibles = document.getElementById("contadorVisibles");
    const btnRestablecer = document.getElementById("btnRestablecerFiltros");
    const contenedorRestablecer = document.getElementById("btnRestablecerContenedor");

    if (contenedorCards) {
        const tarjetas = Array.from(contenedorCards.querySelectorAll(".service-col"));

        // Filtrado en vivo sobre los elementos de la hoja actual
        function aplicarFiltroEnVivo() {
            const texto = (inputBuscador ? inputBuscador.value : "").trim().toLowerCase();
            let visibles = 0;

            tarjetas.forEach(card => {
                const nombre = card.dataset.nombre || "";
                const desc = card.dataset.descripcion || "";
                const tipo = card.dataset.tipo || "";

                const matchTexto = !texto || nombre.includes(texto) || desc.includes(texto) || tipo.includes(texto);

                if (matchTexto) {
                    card.classList.remove("d-none");
                    visibles++;
                } else {
                    card.classList.add("d-none");
                }
            });

            if (sinResultados) {
                sinResultados.classList.toggle("d-none", visibles > 0);
            }
        }

        if (inputBuscador) {
            inputBuscador.addEventListener("input", aplicarFiltroEnVivo);
            
            // Al presionar Enter, envía el formulario para buscar en toda la base de datos
            inputBuscador.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && formFiltros) {
                    formFiltros.submit();
                }
            });
        }

        if (btnLimpiar && inputBuscador) {
            btnLimpiar.addEventListener("click", () => {
                inputBuscador.value = "";
                if (formFiltros) {
                    formFiltros.submit();
                } else {
                    aplicarFiltroEnVivo();
                }
            });
        }

        // Cambio de selectores: envía el formulario para recalcular la paginación de 12 por hoja
        if (selectCategoria && formFiltros) {
            selectCategoria.addEventListener("change", () => formFiltros.submit());
        }

        if (selectDisponibilidad && formFiltros) {
            selectDisponibilidad.addEventListener("change", () => formFiltros.submit());
        }

        if (selectOrdenar && formFiltros) {
            selectOrdenar.addEventListener("change", () => formFiltros.submit());
        }

        // Píldoras / chips de filtrado rápido por categoría
        chipsCategoria.forEach(chip => {
            chip.addEventListener("click", () => {
                const catVal = chip.dataset.categoria;
                if (selectCategoria && formFiltros) {
                    selectCategoria.value = catVal;
                    formFiltros.submit();
                }
            });
        });
    }
    }

    // --------------------------------------------------------------------------
    // 2. TOGGLE INTERACTIVO "VER MÁS DETALLES" / "VER MENOS"
    // --------------------------------------------------------------------------
    const togglesDetalle = document.querySelectorAll(".btn-toggle-detalle");

    togglesDetalle.forEach(btn => {
        const targetSelector = btn.getAttribute("data-bs-target");
        if (!targetSelector) return;

        const targetEl = document.querySelector(targetSelector);
        if (!targetEl) return;

        // Escuchar cuando el colapsable se abre
        targetEl.addEventListener("show.bs.collapse", () => {
            const spanText = btn.querySelector(".btn-text");
            const icon = btn.querySelector(".toggle-icon");
            if (spanText) spanText.textContent = "Ver menos";
            if (icon) {
                icon.classList.remove("bi-chevron-down");
                icon.classList.add("bi-chevron-up");
            }
            btn.classList.add("is-expanded");
        });

        // Escuchar cuando el colapsable se cierra
        targetEl.addEventListener("hide.bs.collapse", () => {
            const spanText = btn.querySelector(".btn-text");
            const icon = btn.querySelector(".toggle-icon");
            if (spanText) spanText.textContent = btn.dataset.textoOriginal || "Ver más detalles";
            if (icon) {
                icon.classList.remove("bi-chevron-up");
                icon.classList.add("bi-chevron-down");
            }
            btn.classList.remove("is-expanded");
        });
    });

    // --------------------------------------------------------------------------
    // 3. COTIZADOR INTERACTIVO A WHATSAPP EN INDEX.HTML
    // --------------------------------------------------------------------------
    const formCotizador = document.getElementById("formCotizadorWeb");
    if (formCotizador) {
        formCotizador.addEventListener("submit", (e) => {
            e.preventDefault();

            const tipoInmueble = document.querySelector('input[name="cotiz_tipo"]:checked')?.value || "No especificado";
            const checkboxes = document.querySelectorAll('input[name="cotiz_serv"]:checked');
            const serviciosElegidos = Array.from(checkboxes).map(c => c.value);

            const nombre = document.getElementById("cotiz_nombre")?.value.trim() || "";
            const telefono = document.getElementById("cotiz_telefono")?.value.trim() || "";
            const ciudad = document.getElementById("cotiz_ciudad")?.value.trim() || "Lago Agrio";
            const mensaje = document.getElementById("cotiz_mensaje")?.value.trim() || "";

            if (!nombre || !telefono) {
                alert("Por favor completa tu nombre y número de teléfono.");
                return;
            }

            let textoWsp = `*NUEVA COTIZACIÓN - WEB GRUPO MEGASEG*\n\n`;
            textoWsp += `👤 *Cliente:* ${nombre}\n`;
            textoWsp += `📞 *Teléfono:* ${telefono}\n`;
            textoWsp += `📍 *Ubicación / Sector:* ${ciudad}\n`;
            textoWsp += `🏢 *Inmueble:* ${tipoInmueble}\n`;
            textoWsp += `🛡️ *Servicios Requeridos:* ${serviciosElegidos.length > 0 ? serviciosElegidos.join(", ") : "Asesoría General"}\n`;
            if (mensaje) {
                textoWsp += `📝 *Detalles:* ${mensaje}\n`;
            }
            textoWsp += `\n_Mensaje generado desde el portal web oficial de Megaseg._`;

            const urlWsp = `https://wa.me/593982900705?text=${encodeURIComponent(textoWsp)}`;
            window.open(urlWsp, "_blank");
        });
    }

    console.log("Grupo Megaseg: Plataforma interactiva cargada correctamente.");
});
