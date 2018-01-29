sudo systemctl stop hostapd.service
sudo systemctl stop dnsmasq.service
sudo systemctl stop dhcpcd.service

sudo systemctl disable hostapd.service
sudo systemctl disable dnsmasq.service

if [ ! -f /etc/dhcpcd.conf.back ]; then
    echo "creating backup of original dhcpcd.conf as dhcpcd.conf.back"
    sudo mv /etc/dhcpcd.conf /etc/dhcpcd.conf.back
fi

sudo cp ./dhcpcd_APoff.conf /etc/dhcpcd.conf

sudo mv /etc/wpa_supplicant/wpa_supplicant.conf.AUS /etc/wpa_supplicant/wpa_supplicant.conf

sudo systemctl start dhcpcd.service
sudo systemctl restart wpa_supplicant.service
sudo systemctl restart networking.service
