[![License][license-shield]](LICENSE.md)

# Proscenic Home Assistant component

A full featured Homeassistant component to control Proscenic vacuum cleaner locally without the cloud.

## Towards Homeassistant official integration

My personal goal is to make this component fully compliant with Homeassistant, so
that it may be added as the official library to handle Proscenic vacuum cleaners.
However, before pushing a PullRequest to the official Homeassistant repository, I would like to share it to some users.
In this way we can test it massively, check it for any bug and make it **robust enough** to be seamlessly integrated
with Homeassistant.

## Component setup

Once the component has been installed, you need to configure it in order to make it work.

First we need to find out the _device_id_, _local key_ of your proscenic vacuum cleaner.

Use tuya-uncover
    git clone https://github.com/blakadder/tuya-uncover.git
    cd tuya-uncover
    pip install requests
    chmod +x uncover.py  
    python uncover.py -v proscenic "email" "password"

## Additional Information

Currently this integration is only tested with a Proscenic 850T, because I only have this one.
Please give me feedback, if it works with other models too.

The integration is communicating locally only, so you can block the access of your vacuum robot to the internet.

If you find a problem/bug or you have a feature request, please open an issue.


