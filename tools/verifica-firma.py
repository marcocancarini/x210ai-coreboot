import sys
from signify.authenticode import AuthenticodeFile
with open(sys.argv[1],'rb') as f:
    af=AuthenticodeFile.from_stream(f)
    print(af.explain_verify()[0])
    for sig in af.iter_embedded_signatures():
        print('digest',sig.digest_algorithm.__name__ if hasattr(sig.digest_algorithm,'__name__') else sig.digest_algorithm)
        si=sig.signer_info
        leaf=[c for c in sig.certificates if c.serial_number==si.serial_number]
        for c in leaf: print('LEAF',c.subject.dn,'| issuer',c.issuer.dn,'|',c.valid_from,'->',c.valid_to,'| sha256',c.sha256_fingerprint if hasattr(c,'sha256_fingerprint') else '')
        print('controfirma',getattr(si.countersigner,'signing_time',None))
