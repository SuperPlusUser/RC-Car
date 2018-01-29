sudo systemctl stop dhcpcd.service
sudo systemctl stop wpa_supplicant.service

if [ ! -f /etc/dhcpcd.conf.back ]; then
    echo "creating backup of original dhcpcd.conf as dhcpcd.conf.back"
    sudo mv /etc/dhcpcd.conf /etc/dhcpcd.conf.back
fi

sudo cp ./dhcpcd_APon.conf /etc/dhcpcd.conf

sudo mv /etc/wpa_supplicant/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf.AUS

sudo systemctl start dhcpcd.service
sudo systemctl start dnsmasq.service
sudo systemctl enable dnsmasq.service

sudo systemctl restart networking.service

sudo systemctl start hostapd.service
sudo systemctl enable hostapd.service
