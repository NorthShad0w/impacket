#!/usr/bin/env python
# coding=utf-8

# 3.1.2.5.1.6
# Use IObjectExporter::ServerAlive2 (opnum 5) to get interface ip address

import argparse
from struct import pack, unpack

from impacket.dcerpc.v5 import dcomrt, rpcrt, transport
from impacket.uuid import uuidtup_to_bin

# constants
AUTH_LEVEL = rpcrt.RPC_C_AUTHN_LEVEL_NONE

IID_IOBJECT_EXPORTER = uuidtup_to_bin(("99fcfec4-5260-101b-bbcb-00aa0021347a", "0.0"))


def main(target_ip, endpoint):
    string_binding = r"ncacn_ip_tcp:%s[%s]" % (
        target_ip,
        endpoint,
    )
    rpc_transport = transport.DCERPCTransportFactory(string_binding)

    dcerpc_v5_portmap = rpc_transport.get_dce_rpc()
    dcerpc_v5_portmap.connect()
    dcerpc_v5_portmap.bind(IID_IOBJECT_EXPORTER)
    req_ServerAlive2 = dcomrt.ServerAlive2()
    resp_ServerAlive2 = dcerpc_v5_portmap.request(req_ServerAlive2)

    # parsing the response

    # response bytes structure Link:
    # https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-dcom/c898afd6-b75d-4641-a2cd-b50cb9f5556d
    p_com_version = resp_ServerAlive2["pComVersion"]
    com_version_tuple = unpack(
        "H" * (len(p_com_version.getData()) // 2), p_com_version.getData()
    )
    major_com_version = com_version_tuple[0]
    minor_com_version = com_version_tuple[1]
    # I have no idea why major version is smaller than minor version

    print("[*] current DCOM major COM version: %d" % major_com_version)
    print("[*] current DCOM minor COM version: %d" % minor_com_version)

    # Or get the number directly
    # print(resp_ServerAlive2["pComVersion"]["MajorVersion"])

    print("[*] NumEntries:", resp_ServerAlive2["ppdsaOrBindings"]["wNumEntries"])
    print(
        "[*] SecurityOffset:", resp_ServerAlive2["ppdsaOrBindings"]["wSecurityOffset"]
    )

    # the name is string array but it is unsigned short array acctually little endian
    string_array = resp_ServerAlive2["ppdsaOrBindings"]["aStringArray"]

    print(string_array)

    # for x in string_array:
    #     print(x)

    oxids = b"".join(
        pack("<H", x) for x in resp_ServerAlive2["ppdsaOrBindings"]["aStringArray"]
    )
    str_bindings = oxids[: resp_ServerAlive2["ppdsaOrBindings"]["wSecurityOffset"] * 2]

    done = False
    string_bindings = list()
    while not done:
        if str_bindings[0:1] == b"\x00" and str_bindings[1:2] == b"\x00":
            done = True
        else:
            binding = dcomrt.STRINGBINDING(str_bindings)
            string_bindings.append(binding)
            str_bindings = str_bindings[len(binding) :]
    for binding in string_bindings:
        ip_address = binding["aNetworkAddr"]
        print(ip_address)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("target_ip", action="store", help="target machine ip address")
    parser.add_argument(
        "endpoint",
        action="store",
        default=" ",
        help="endpoint to build stringbinding 135 or endpoint=135",
    )
    args = parser.parse_args()

    target_ip = args.target_ip
    endpoint = args.endpoint

    main(target_ip, endpoint)
