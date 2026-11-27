package com.g2jackob.tuim.domain

object Validation {
    fun validateName(name: String): String? =
        if (name.trim().isEmpty()) "Nazwa nie może być pusta" else null

    fun validateQuantity(quantity: Double?): String? =
        if (quantity == null || quantity <= 0.0) "Ilość musi być większa od zera" else null

    fun validatePrice(price: Double?): String? =
        if (price != null && price < 0.0) "Cena nie może być ujemna" else null
}
