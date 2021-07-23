set MENU_DIR="%PREFIX%\Menu"
if not exist %MENU_DIR% mkdir %MENU_DIR%

:: icon is in public domain: https://github.com/paomedia/small-n-flat

copy "%RECIPE_DIR%\console_shortcut.ico" %MENU_DIR%
copy "%RECIPE_DIR%\console_shortcut.json" %MENU_DIR%
