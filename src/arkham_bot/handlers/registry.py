import logging

from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..core.config import CALLBACK_CANCEL, CHOOSING_CARD_NUMBER, SEARCH_WAITING_QUERY
from .card_handler import (
    button_callback,
    cancel_conversation,
    card_command,
    card_list_page_callback,
    receive_card_number,
)
from .cotd_handler import (
    cotd_back_callback,
    cotd_command,
    cotd_month_callback,
    cotd_year_callback,
)
from .decklist_handler import decklist_command
from .faq_handler import faq_command
from .search_handler import (
    search_card_selected,
    search_command,
    search_page_callback,
    search_receive_query,
)
from .sets_handler import (
    set_browse_callback,
    sets_back_callback,
    sets_command,
    sets_list_page_callback,
)
from .status_handler import start_command, status_command
from .taboo_handler import (
    taboo_back_callback,
    taboo_card_callback,
    taboo_category_callback,
    taboo_command,
    taboo_list_select_callback,
    taboo_lists_back_callback,
    taboo_page_callback,
)

logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """Logs unhandled Telegram handler errors without exposing details to users."""
    logger.exception("Unhandled Telegram handler error", exc_info=context.error)


def register_handlers(application):
    """Registers Telegram command and callback handlers."""
    card_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("card", card_command)],
        states={
            CHOOSING_CARD_NUMBER: [
                CallbackQueryHandler(card_list_page_callback, pattern=r'^CARD_LIST_p'),
                CallbackQueryHandler(button_callback, pattern='^SEARCH_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_card_number)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start_command),
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"),
        ],
        per_message=False,
    )

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("faq", faq_command))
    application.add_handler(CommandHandler("taboo", taboo_command))
    application.add_handler(CallbackQueryHandler(taboo_list_select_callback, pattern=r'^TABOO_LIST_'))
    application.add_handler(CallbackQueryHandler(taboo_lists_back_callback, pattern=r'^TABOO_LISTS$'))
    application.add_handler(CallbackQueryHandler(taboo_page_callback, pattern=r'^TABOO_PAGE_'))
    application.add_handler(CallbackQueryHandler(taboo_category_callback, pattern=r'^TABOO_CAT_'))
    application.add_handler(CallbackQueryHandler(taboo_card_callback, pattern=r'^TABOO_CARD_'))
    application.add_handler(CallbackQueryHandler(taboo_back_callback, pattern=r'^TABOO_BACK$'))
    application.add_handler(CommandHandler("decklist", decklist_command))
    search_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("search", search_command)],
        states={
            SEARCH_WAITING_QUERY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, search_receive_query),
                CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_conversation),
            CommandHandler("start", start_command),
            CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"),
        ],
        per_message=False,
    )
    application.add_handler(search_conv_handler)
    application.add_handler(CallbackQueryHandler(search_card_selected, pattern=r'^CARD_SELECT_'))
    application.add_handler(CallbackQueryHandler(search_page_callback, pattern=r'^SEARCH_PAGE_\d+$'))
    application.add_handler(CommandHandler("sets", sets_command))
    application.add_handler(CallbackQueryHandler(set_browse_callback, pattern=r'^SET_BROWSE_'))
    application.add_handler(CallbackQueryHandler(sets_back_callback, pattern=r'^SETS_BACK'))
    application.add_handler(CallbackQueryHandler(sets_list_page_callback, pattern=r'^SET_LIST_p'))
    application.add_handler(CommandHandler("cotd", cotd_command))
    application.add_handler(CallbackQueryHandler(cotd_year_callback, pattern=r'^COTD_YEAR_\d+$'))
    application.add_handler(CallbackQueryHandler(cotd_month_callback, pattern=r'^COTD_MONTH_\d+_\d+$'))
    application.add_handler(CallbackQueryHandler(cotd_back_callback, pattern=r'^COTD_BACK$'))
    application.add_handler(card_conv_handler)
    application.add_handler(CallbackQueryHandler(cancel_conversation, pattern=f"^{CALLBACK_CANCEL}$"))
    application.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^NOOP$"))
    application.add_error_handler(error_handler)
