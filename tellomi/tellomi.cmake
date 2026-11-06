# Tellomi build switch. Default ON.
# OFF is an explicit upstream comparison build and is not a Tellomi package.
# ON does not implement MTProto. Configure still succeeds so the fail-closed
# binary can be produced; that binary stops before opening a connection.

option(TELLOMI_BUILD "Build the Tellomi client. Refuses Telegram production DCs, RSA, and autoupdate." ON)

if (DEFINED CMAKE_SCRIPT_MODE_FILE)
    if (NOT TELLOMI_BUILD)
        message(FATAL_ERROR "TELLOMI_BUILD must default to ON")
    endif()
    message(STATUS "TELLOMI_BUILD default ON")
    return()
endif()

if (TELLOMI_BUILD)
    add_compile_definitions(TELLOMI_BUILD)
    set(DESKTOP_APP_DISABLE_AUTOUPDATE ON CACHE BOOL
        "Tellomi does not use Telegram Desktop autoupdate." FORCE)
    set(DESKTOP_APP_DISABLE_CRASH_REPORTS ON CACHE BOOL
        "Tellomi does not send crash reports to tdesktop.com." FORCE)
    message(STATUS "Tellomi build: MTProto not implemented; autoupdate and crash upload off")
endif()
