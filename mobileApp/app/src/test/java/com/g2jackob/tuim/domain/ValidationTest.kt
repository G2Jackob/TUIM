package com.g2jackob.tuim.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ValidationTest {
    @Test
    fun `blank name is rejected`() {
        assertEquals("Nazwa nie może być pusta", Validation.validateName("   "))
    }

    @Test
    fun `valid name is accepted`() {
        assertNull(Validation.validateName("Mleko"))
    }

    @Test
    fun `zero quantity is rejected`() {
        assertEquals("Ilość musi być większa od zera", Validation.validateQuantity(0.0))
    }

    @Test
    fun `negative quantity is rejected`() {
        assertEquals("Ilość musi być większa od zera", Validation.validateQuantity(-2.0))
    }

    @Test
    fun `positive quantity is accepted`() {
        assertNull(Validation.validateQuantity(1.5))
    }

    @Test
    fun `null quantity is rejected`() {
        assertEquals("Ilość musi być większa od zera", Validation.validateQuantity(null))
    }
}
