-- Activate Safari Extension Automatically
-- This script opens Safari Tech Preview and enables the NFA SEFAZ PB extension

tell application "Safari Technology Preview"
    activate
    delay 2
end tell

tell application "System Events"
    tell process "Safari Technology Preview"
        -- Open Preferences (Cmd+,)
        keystroke "," using command down
        delay 2

        -- Click Extensions tab
        try
            set extensionsButton to button "Extensions" of toolbar 1 of window 1
            click extensionsButton
            delay 2

            -- Find extension in list
            set foundExtension to false
            try
                set extensionTable to table 1 of scroll area 1 of group 1 of window 1
                set extensionRows to rows of extensionTable

                repeat with aRow in extensionRows
                    try
                        set rowName to name of aRow as string
                        if rowName contains "NFA SEFAZ PB" or rowName contains "NFASEFAZPB" then
                            set extensionCheckbox to checkbox 1 of aRow
                            if value of extensionCheckbox is false then
                                click extensionCheckbox
                                set foundExtension to true
                                delay 1
                                exit repeat
                            else
                                set foundExtension to true
                                exit repeat
                            end if
                        end if
                    end try
                end repeat
            end try

            if foundExtension then
                -- Click "Edit Websites..." to allow domain
                try
                    click button "Edit Websites..." of group 1 of window 1
                    delay 1

                    -- Allow sefaz.pb.gov.br
                    try
                        set websiteTable to table 1 of scroll area 1 of window 1
                        -- Search for sefaz domain
                        keystroke "sefaz" -- Type to filter
                        delay 1

                        -- Allow access
                        try
                            set sefazRow to first row of websiteTable whose name contains "sefaz"
                            set popup of sefazRow to "Allow"
                            delay 1
                        end try
                    end try

                    -- Close Edit Websites window
                    keystroke "w" using command down
                    delay 1
                end try
            end if

            -- Close Preferences
            keystroke "w" using command down

        on error errorMessage
            -- If anything fails, just close preferences
            try
                keystroke "w" using command down
            end try
            return "Error: " & errorMessage
        end try
    end tell
end tell

return "Extension activation completed"

