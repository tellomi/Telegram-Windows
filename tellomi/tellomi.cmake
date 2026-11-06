# Tellomi build switch for the imported Telegram Desktop tree.
# OFF leaves upstream behavior unchanged.
# ON does not embed a datacenter address, an API hash, or an RSA key.

if (DEFINED CMAKE_SCRIPT_MODE_FILE)
    message(STATUS "tellomi.cmake parsed")
    return()
endif()

option(TELLOMI_BUILD "Build the Tellomi chat client. Refuses Telegram production DCs." OFF)

if (TELLOMI_BUILD)
    add_compile_definitions(TELLOMI_BUILD)
    set(DESKTOP_APP_DISABLE_AUTOUPDATE ON CACHE BOOL
        "Tellomi does not use Telegram Desktop autoupdate." FORCE)
    message(STATUS "Tellomi build: chat only, autoupdate off, DCs from TELLOMI_DC_CONFIG")
endif()
