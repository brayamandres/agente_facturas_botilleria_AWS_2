# Evaluación Formal del Modelo de Machine Learning (Indicadores IE1, IE2, IE5 e IE10)

## 1. Especificación del Modelo e Hiperparámetros (Rúbrica Sección 1.1.a)
* **Framework:** Scikit-Learn 1.9 / Python 3.11 (Compatible con contenedor AWS SageMaker Scikit-Learn).
* **Tipo de Modelo:** Pipeline NLP Supervisado (TF-IDF Vectorizer + Multinomial Logistic Regression).
* **Espacio de Características (Features):** N-Gramas de palabras `ngram_range=(1, 2)`, sublinear TF habilitado, máximo `1500` características léxicas.
* **Regularización y Optimización:** Inverso de regularización $C=2.0$, ponderación de clases `class_weight='balanced'` para evitar sesgo, función de pérdida multinomial con solver L-BFGS.

---

## 2. Dataset de Entrenamiento y Validación (Rúbrica Sección 1.1.a y IE5)
* **Archivo de Datos:** `data/dataset_facturas_entrenamiento.csv`
* **Población Total:** 150 glosas comerciales extraídas de facturas de distribuidores chilenos (CCU, Embonor, Capel, Concha y Toro, Diageo, AB InBev).
* **Composición de Dificultad (Estrés del Modelo):**
  * **Casos Estándar / Limpios (70%):** 105 registros con glosas completas de distribuidores.
  * **Casos Difíciles y Ruidosos (30%):** 45 registros con abreviaturas severas (e.g., `MST 35 750`, `JW BLK`), errores OCR (e.g., `PISC0 M1STRAL`, `CERV CROONA`) y packs cruzados (e.g., `COMBO PISCOLA MISTRAL + COCA`).
* **Partición de Datos:**
  * **Conjunto de Entrenamiento (80%):** 120 registros.
  * **Conjunto de Evaluación Ciega / Test (20%):** 30 registros (estratificado para preservar proporciones de clase).

---

## 3. Métricas Oficiales de Rendimiento (Rúbrica Sección 2.3.d / IE10)

| Métrica de Evaluación | Valor Obtenido | Umbral de Calidad Mínimo | Estado de Aprobación |
| :--- | :---: | :---: | :---: |
| **Exactitud (Accuracy)** | **96.67%** | > 85.0% | **DESTACADO (> 90%)** |
| **Precisión Ponderada (Precision)** | **97.14%** | > 80.0% | **DESTACADO (> 90%)** |
| **Sensibilidad Ponderada (Recall)** | **96.67%** | > 80.0% | **DESTACADO (> 90%)** |
| **F1-Score Ponderado (F1-Weighted)** | **96.64%** | > 80.0% | **DESTACADO (> 90%)** |
| **F1-Score Macro (F1-Macro)** | **96.64%** | > 80.0% | **DESTACADO (> 90%)** |

---

## 4. Desglose Detallado por Categoría de Producto

| Categoría Comercial | Precisión (Precision) | Cobertura (Recall) | F1-Score | Muestras (Support) |
| :--- | :---: | :---: | :---: | :---: |
| **Bebidas y Analcohólicos** | 100.0% | 100.0% | **100.0%** | 6 |
| **Cervezas** | 100.0% | 100.0% | **100.0%** | 6 |
| **Destilados - Pisco** | 100.0% | 100.0% | **100.0%** | 6 |
| **Destilados - Whisky / Otros** | 85.7% | 100.0% | **92.3%** | 6 |
| **Vinos** | 100.0% | 83.3% | **90.9%** | 6 |


---

## 5. Matriz de Confusión (Confusion Matrix) y Análisis de Casos Borde

| Categoría Real / Predicción | Bebidas y Analcohólicos | Cervezas | Destilados - Pisco | Destilados - Whisky / Otros | Vinos |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Bebidas y Analcohólicos** | 6 | 0 | 0 | 0 | 0 |
| **Cervezas** | 0 | 6 | 0 | 0 | 0 |
| **Destilados - Pisco** | 0 | 0 | 6 | 0 | 0 |
| **Destilados - Whisky / Otros** | 0 | 0 | 0 | 6 | 0 |
| **Vinos** | 0 | 0 | 0 | 1 | 5 |


* **Análisis de la Matriz:**
  * 29 de las 30 muestras del conjunto de prueba ciego fueron clasificadas con total exactitud (**96.67% de exactitud global**).
  * La única discrepancia observada ocurrió con la glosa ultra-abreviada `"TARA ET NGR 750ML"` (Vino Tarapacá Etiqueta Negra), clasificada probabilísticamente como `Destilados - Whisky / Otros` debido a la fuerte asociación léxica del n-grama `"ET NGR"` ("Etiqueta Negra") con el whisky Johnnie Walker.
  * **Comportamiento Seguro:** Ante esta ambigüedad léxica, la probabilidad calculada por el modelo fue de apenas **55.78%**, ubicándose muy por debajo del umbral de negocio del **85%**. Por consiguiente, el sistema activa automáticamente la derivación a **Revisión Humana (Human-in-the-Loop)**, evitando asignaciones erróneas en el inventario.

---

## 6. Interpretabilidad y Explicabilidad para Toma de Decisiones (IE2)
El modelo entrenado no actúa como caja negra:
1. **Extracción de Coeficientes:** Los coeficientes de la regresión logística permiten identificar qué tokens específicos de la glosa comercial determinaron la clase predicha (por ejemplo, `['mistral', 'pisc']` para *Destilados - Pisco*).
2. **Confianza Probabilística:** Mediante `predict_proba()` se calcula la certeza porcentual matemática.
3. **Regla de Negocio (HITL):** Si $\text{confianza} \ge 0.85$, se habilita la asignación automática en inventario; si $\text{confianza} < 0.85$, se desvía a revisión humana.
