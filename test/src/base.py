import asyncio
import traceback

def fmt_error(e: Exception):
    return "\n".join(traceback.format_exception(e))

def fail_test():
    raise Exception("failed")
    
def pass_test():
    raise Exception("passed")

def check_pass(e: Exception):
    if e.args[0] == "passed":
        return True, ""
    
    elif e.args[0] == "failed":
        return False, ""
    
    else:
        return False, fmt_error(e)

class UnitTest:    
    async def test(self) -> bool:
        raise NotImplementedError
    
def run_tests(tests: list[UnitTest]):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    passed = 0
    failed = 0
    
    print("Running tests\n")
    
    for i, test in enumerate(tests):
        print(f"{i+1}/{len(tests)}: ", end="")
        
        try:
            val, exc = loop.run_until_complete(test.test())
        
            if val:
                print("\033[32mTest passed\033[0m")
                passed += 1
            
            else:
                print(f"\033[31mTest failed: {type(test)}\033[0m")
                print(exc)
                print()
                
                failed += 1
                
        except Exception as e:
            print(f"\033[31mTest failed: {type(test)}\033[0m")
            print(e)
            print()
            
            failed += 1
        
    print(f"\033[37mAll: {len(tests)}\033[0m | \033[32mPassed: {passed}\033[0m | \033[31mFailed: {failed}\033[0m")