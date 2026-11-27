package com.g2jackob.tuim.data.network

import com.google.gson.Gson
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BackendDtoTest {
    private val gson = Gson()

    @Test
    fun `item dto reads backend purchased flag and nested reservation owner`() {
        val item = gson.fromJson(
            """
                {
                  "id": "item-1",
                  "name": "Mleko",
                  "quantity": "2.000",
                  "unit": "l",
                  "is_purchased": true,
                  "reserved_by": {
                    "id": 7,
                    "username": "alice",
                    "display_name": "Alice"
                  }
                }
            """.trimIndent(),
            ShoppingItemDto::class.java
        )

        assertTrue(item.purchased)
        assertEquals(2.0, item.quantity, 0.0)
        assertEquals("Alice", item.reservedBy?.label())
    }

    @Test
    fun `list total dto reads backend currency conversion`() {
        val total = gson.fromJson(
            """
                {
                  "currency": "PLN",
                  "total": "25.00",
                  "items_priced": 2,
                  "items_without_price": 1,
                  "converted": {
                    "currency": "EUR",
                    "total": "5.80",
                    "rate": "0.232",
                    "rate_date": "2026-11-27",
                    "stale": false
                  }
                }
            """.trimIndent(),
            ListTotalDto::class.java
        )

        assertEquals("25.00", total.total)
        assertEquals("EUR", total.converted?.currency)
        assertFalse(total.converted?.stale ?: true)
    }

    @Test
    fun `list dto reads ownership archive and item counts`() {
        val list = gson.fromJson(
            """
                {
                  "id": "list-1",
                  "name": "Zakupy",
                  "currency": "PLN",
                  "is_archived": true,
                  "role": "member",
                  "items_count": 4,
                  "purchased_count": 2
                }
            """.trimIndent(),
            ShoppingListDto::class.java
        )

        assertTrue(list.isArchived)
        assertEquals("member", list.role)
        assertEquals(4, list.itemsCount)
        assertEquals(2, list.purchasedCount)
    }

    @Test
    fun `member invite and exchange rate dto map backend fields`() {
        val member = gson.fromJson(
            """
                {
                  "user": {"id": 7, "username": "alice", "display_name": "Alice"},
                  "role": "member",
                  "joined_at": "2026-11-27T14:00:00Z"
                }
            """.trimIndent(),
            ListMemberDto::class.java
        )
        val invite = gson.fromJson(
            """{"code":"ABCD1234","list_id":"list-1","expires_at":"2026-11-28T14:00:00Z"}""",
            InviteDto::class.java
        )
        val rate = gson.fromJson(
            """{"from":"PLN","to":"EUR","rate":"0.23","rate_date":"2026-11-27","stale":true}""",
            ExchangeRateDto::class.java
        )

        assertEquals("Alice", member.user.label())
        assertEquals("member", member.role)
        assertEquals("list-1", invite.listId)
        assertEquals("ABCD1234", invite.code)
        assertEquals("EUR", rate.toCurrency)
        assertTrue(rate.stale)
    }

    @Test
    fun `item create request uses backend field names`() {
        val request = gson.toJson(
            ShoppingItemRequest(
                name = "Mleko",
                quantity = 2.0,
                unit = "szt",
                category = "Nabiał",
                note = "bez laktozy",
                estimatedPrice = 3.5
            )
        )

        assertTrue(request.contains("\"estimated_price\":3.5"))
        assertTrue(request.contains("\"unit\":\"szt\""))
        assertTrue(request.contains("\"category\":\"Nabiał\""))
    }
}
