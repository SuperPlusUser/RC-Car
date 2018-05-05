echo -e '\x00=/SRCCP/v0.1/#<cmd><name>drive</name><speed>90</speed></cmd>#/' | nc 127.0.0.1 8889

echo -e '\x00=/SRCCP/v0.1/#<cmd><name>steer</name><angle>90</angle></cmd>#/' | nc 127.0.0.1 8889