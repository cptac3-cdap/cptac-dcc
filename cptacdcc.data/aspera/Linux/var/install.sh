#!/bin/sh

DEBUG=1

if [ "_$1" = "_-q" ]; then
    DEBUG=0
fi

say()
{
    if [ $DEBUG -eq 1 ]; then echo $1; fi
}

INSTALL_DIR=$1

if [ $(id -u) = 0 ]; then
	echo "This script cannot be run as root, Aspera Connect must be installed per user."
	exit 1
else
	echo "Deploying Aspera Connect ($INSTALL_DIR) for the current user only."
	# Kill all asperaconnect instances
	if [ -n "$(pgrep -u `whoami` asperaconnect)" ]; then
		echo "Aspera Connect is running, Attempting to close it."
		pkill -u `whoami` asperaconnect
		if [ -n "$(pgrep -u `whoami` asperaconnect)" ]; then
			echo "Failed to close Aspera Connect, Attempting to kill it."
			pkill -9 -u `whoami` asperaconnect
			if [ -n "$(pgrep -u `whoami` asperaconnect)" ]; then
				echo "Failed to close Aspera Connect, please do it manually and rerun the installer."
				exit 1
			fi
		fi
	fi
	# Create asperaconnect.path file
	mkdir -p ~/.aspera/connect/etc 2>/dev/null || echo "Unable to create .aspera directory in $HOME. Aspera Connect will not work" 
	echo $INSTALL_DIR/bin > $INSTALL_DIR/etc/asperaconnect.path

	# Place .desktop file
	mkdir -p ~/.local/share/applications
	rm -rf ~/.local/share/applications/aspera-connect.desktop 2>/dev/null
	cp $INSTALL_DIR/res/aspera-connect.desktop ~/.local/share/applications/

	# Deploy mozilla plug-in
	mkdir -p ~/.mozilla/plugins
	rm -rf ~/.mozilla/plugins/libnpasperaweb*.so* 2>/dev/null
	cp $INSTALL_DIR/lib/libnpasperaweb*.so ~/.mozilla/plugins

	# Register protocol handler
	xdg-mime default aspera-connect.desktop x-scheme-handler/fasp 2>/dev/null || echo "Unable to register protocol handler, Aspera Connect won't be able to auto-launch" 

	echo "Restart firefox manually to load the Aspera Connect plug-in"

	echo
	echo "Install complete."
fi
