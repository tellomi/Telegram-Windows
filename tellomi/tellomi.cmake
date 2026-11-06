# Tellomi build switch. Default ON.
# OFF is an explicit upstream comparison build and is not a Tellomi package.
# ON compiles the dev DC and the mobile server RSA into DcOptions.
# It still does not log in or send messages by itself.

option(TELLOMI_BUILD "Build the Tellomi client. Uses the Tellomi dev DC and server RSA, and refuses Telegram production DCs, Telegram RSA, and autoupdate." ON)

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
    message(STATUS "Tellomi build: dev DC and server RSA compiled in; autoupdate and crash upload off")
endif()
