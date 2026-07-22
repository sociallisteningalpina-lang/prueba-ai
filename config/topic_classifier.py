#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Clasificador de Temas para Comentarios de Campañas
Personalizable por campaña/producto
"""

import re
from typing import Callable


def create_topic_classifier() -> Callable[[str], str]:
    """
    Retorna una función de clasificación de temas personalizada para esta campaña.
    
    Returns:
        function: Función que toma un comentario (str) y retorna un tema (str)
    
    Usage:
        classifier = create_topic_classifier()
        tema = classifier("¿Dónde puedo comprar este producto?")
        # tema = 'Preguntas sobre el Producto'
    """
    
    def classify_topic(comment: str) -> str:
        """
        Clasifica un comentario en un tema específico basado en patrones regex.
        
        Args:
            comment: Texto del comentario a clasificar
            
        Returns:
            str: Nombre del tema asignado
        """
        comment_lower = str(comment).lower()
        
        # CATEGORÍA 1: Preguntas sobre el Producto
        if re.search(
            r'\bprecio\b|\bcu[aá]nto vale\b|d[oó]nde|c[oó]mo consigo|'
            r'duda|pregunta|comprar|tiendas|disponible|sirve para|'
            r'c[oó]mo se toma|tiene az[uú]car|valor',
            comment_lower
        ):
            return 'Preguntas sobre el Producto'
        
        # CATEGORÍA 2: Comparación con Kéfir Casero/Artesanal
        if re.search(
            r'b[úu]lgaros|n[oó]dulos|en casa|casero|artesanal|'
            r'preparo yo|vendo el cultivo|hecho por mi',
            comment_lower
        ):
            return 'Comparación con Kéfir Casero/Artesanal'
        
        # CATEGORÍA 3: Ingredientes y Salud
        if re.search(
            r'aditivos|almid[oó]n|preservantes|lactosa|microbiota|'
            r'flora intestinal|saludable|bacterias|vivas|gastritis|'
            r'colon|helicobacter|az[uú]car añadid[oa]s',
            comment_lower
        ):
            return 'Ingredientes y Salud'
        
        # CATEGORÍA 4: Competencia y Disponibilidad
        if re.search(
            r'pasco|\b[eé]xito\b|\bara\b|ol[ií]mpica|d1|'
            r'copia de|no lo venden|no llega|no lo encuentro|no hay en',
            comment_lower
        ):
            return 'Competencia y Disponibilidad'
        
        # CATEGORÍA 5: Opinión General del Producto
        if re.search(
            r'rico|bueno|excelente|gusta|mejor|delicioso|espectacular|'
            r'encanta|s[úu]per|feo|horrible|mal[ií]simo|sabe a',
            comment_lower
        ):
            return 'Opinión General del Producto'
        
        # CATEGORÍA 6: Fuera de Tema / No Relevante
        if re.search(
            r'am[eé]n|jajaja|receta|gracias|bendiciones',
            comment_lower
        ) or len(comment_lower.split()) < 3:
            return 'Fuera de Tema / No Relevante'
        
        # CATEGORÍA DEFAULT: Otros
        return 'Otros'
    
    return classify_topic


# ============================================================================
# METADATA DE LA CAMPAÑA (OPCIONAL)
# ============================================================================

CAMPAIGN_METADATA = {
    'campaign_name': 'Alpina - Kéfir',
    'product': 'Kéfir Alpina',
    'categories': [
        'Preguntas sobre el Producto',
        'Comparación con Kéfir Casero/Artesanal',
        'Ingredientes y Salud',
        'Competencia y Disponibilidad',
        'Opinión General del Producto',
        'Fuera de Tema / No Relevante',
        'Otros'
    ],
    'version': '1.0',
    'last_updated': '2025-11-20'
}


def get_campaign_metadata() -> dict:
    """Retorna metadata de la campaña"""
    return CAMPAIGN_METADATA.copy()
