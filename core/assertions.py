# assertion.py
from contextvars import ContextVar

# Tworzenie context variables
_current_framework = ContextVar("framework", default=None)
_current_group_name = ContextVar("group_name", default=None)
_current_test_name = ContextVar("test_name", default=None)

def set_test_context(framework, group_name, test_name):
    """
    Ustawia globalny kontekst testu.
    :param framework: Instancja frameworku testowego.
    :param group_name: Nazwa grupy testowej.
    :param test_name: Nazwa testu.
    """
    _current_framework.set(framework)
    _current_group_name.set(group_name)
    _current_test_name.set(test_name)

def clear_test_context():
    """
    Czyści globalny kontekst testu.
    """
    _current_framework.set(None)
    _current_group_name.set(None)
    _current_test_name.set(None)

def _get_context(context=None):
    return {
        "framework": context.get("framework") if context else _current_framework.get(),
        "group_name": context.get("group_name") if context else _current_group_name.get(),
        "test_name": context.get("test_name") if context else _current_test_name.get(),
    }

def TEST_FAIL_MESSAGE(message, context=None):
    """
    Asercja raportująca niepowodzenie testu z podanym komunikatem.
    Jeśli kontekst (context) jest dostępny, raportuje wynik przez framework.
    Jeśli brak kontekstu, przechowuje symbol do późniejszego wykonania.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        ctx["framework"].report_test_result(
            ctx["group_name"],
            ctx["test_name"],
            False,
            message
        )
    else:
        return ("TEST_FAIL_MESSAGE", message)

def TEST_INFO_MESSAGE(message, context=None):
    """
    Loguje wiadomość informacyjną z podanym komunikatem.
    Jeśli kontekst (context) jest dostępny, używa frameworka do logowania.
    Jeśli brak kontekstu, przechowuje symbol do późniejszego wykonania.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        ctx["framework"].report_test_info(
            ctx["group_name"],
            ctx["test_name"],
            message
        )
    else:
        return ("TEST_INFO_MESSAGE", message)

def TEST_ASSERT_EQUAL(expected, actual, context=None):
    """
    Symboliczna asercja sprawdzająca równość.
    :param actual: Aktualna wartość.
    :param expected: Oczekiwana wartość.
    :param context: (Opcjonalny) Słownik zawierający framework, grupę i nazwę testu.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        if expected != actual:
            ctx["framework"].report_test_result(
                ctx["group_name"],
                ctx["test_name"],
                False,
                f"Assertion failed! Expected = {expected}, actual = {actual}"
            )
        else:
            ctx["framework"].report_test_result(ctx["group_name"], ctx["test_name"], True)
    else:
        return ("TEST_ASSERT_EQUAL", actual, expected)

def TEST_ASSERT_TRUE(condition, context=None):
    """
    Symboliczna asercja sprawdzająca, czy warunek jest prawdziwy.
    :param condition: Warunek do sprawdzenia.
    :param context: (Opcjonalny) Słownik zawierający framework, grupę i nazwę testu.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        if not condition:
            ctx["framework"].report_test_result(
                ctx["group_name"],
                ctx["test_name"],
                False,
                "Assertion failed: condition is not true"
            )
        else:
            ctx["framework"].report_test_result(ctx["group_name"], ctx["test_name"], True)
    else:
        return ("TEST_ASSERT_TRUE", condition)

def TEST_ASSERT_IN(item, collection, context=None):
    """
    Symboliczna asercja sprawdzająca, czy element znajduje się w kolekcji.
    :param item: Element do sprawdzenia.
    :param collection: Kolekcja, w której szukamy elementu.
    :param context: (Opcjonalny) Słownik zawierający framework, grupę i nazwę testu.
    """
    ctx = _get_context(context)
    if ctx["framework"]:
        if item not in collection:
            ctx["framework"].report_test_result(
                ctx["group_name"],
                ctx["test_name"],
                False,
                f"Assertion failed: {item} not in {collection}"
            )
        else:
            ctx["framework"].report_test_result(ctx["group_name"], ctx["test_name"], True)
    else:
        return ("TEST_ASSERT_IN", item, collection)
